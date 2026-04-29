"""Migrate the on-disk knowledge base into Plane native Pages.

For every workspace that already has a FUND project we:

1. Get-or-create a sibling project ``Knowledge Base`` (identifier ``KB``).
2. Walk ``KB_PATH`` recursively. Each directory becomes a parent Page;
   each ``.md``/``.txt`` file becomes a child Page rendered as HTML.
3. Binary files (PDF, DOCX, PPTX, images, spreadsheets) are uploaded as
   ``FileAsset`` objects attached to the same KB project. A stub Page is
   created with extracted text (``pypdf``/``python-docx``) plus a download
   link, so the chat assistant can search them like any other page.
4. ``Page.external_id`` carries the original relative path so the importer
   is fully idempotent — re-running it updates in place rather than
   duplicating, and we can later resolve ``FundingOpportunity.linked_docs``
   filesystem paths back to page UUIDs.

Usage::

    python manage.py import_kb_to_pages              # do it for real
    python manage.py import_kb_to_pages --dry-run    # report only
    python manage.py import_kb_to_pages --workspace funding-cockpit
"""

from __future__ import annotations

import hashlib
import io
import logging
import os

import markdown
from django.core.management.base import BaseCommand
from django.db import transaction

from plane.db.models import (
    FileAsset,
    Page,
    Project,
    ProjectIdentifier,
    ProjectMember,
    ProjectPage,
    Workspace,
    WorkspaceMember,
)

logger = logging.getLogger("plane.funding.import_kb")

KB_PATH = os.environ.get("KB_PATH", "/app/kb")
KB_PROJECT_IDENTIFIER = "KB"
KB_PROJECT_NAME = "Knowledge Base"

TEXT_EXTS = {".md", ".txt", ".markdown"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}
BINARY_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".zip"}


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None


def _md_to_html(content: str) -> str:
    return markdown.markdown(
        content,
        extensions=["codehilite", "fenced_code", "tables", "toc"],
    )


def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)[:200_000]
    except Exception as exc:
        return f"_(PDF text extraction failed: {exc})_"


def _extract_docx(path: str) -> str:
    try:
        import docx  # python-docx

        doc = docx.Document(path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text)[:200_000]
    except Exception as exc:
        return f"_(DOCX text extraction failed: {exc})_"


def _title_from_markdown(content: str, fallback: str) -> str:
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()[:200]
    return fallback


class Command(BaseCommand):
    help = "Import the on-disk KB into Plane native Pages"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--workspace",
            default=None,
            help="Workspace slug to import into; defaults to all workspaces with a FUND project.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        slug = options["workspace"]

        if not os.path.isdir(KB_PATH):
            self.stderr.write(f"KB_PATH does not exist: {KB_PATH}")
            return

        workspaces_qs = Workspace.objects.all()
        if slug:
            workspaces_qs = workspaces_qs.filter(slug=slug)
        workspaces = [
            ws
            for ws in workspaces_qs
            if Project.objects.filter(workspace=ws, identifier="FUND").exists()
        ]
        if not workspaces:
            self.stderr.write("No workspaces with a FUND project found.")
            return

        for workspace in workspaces:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nWorkspace: {workspace.slug}"))
            self._import_into_workspace(workspace, dry_run=dry)

    # ------------------------------------------------------------------ helpers

    def _ensure_kb_project(self, workspace: Workspace) -> Project:
        owner = workspace.owner
        project, created = Project.objects.get_or_create(
            workspace=workspace,
            identifier=KB_PROJECT_IDENTIFIER,
            defaults={
                "name": KB_PROJECT_NAME,
                "description": "Funding knowledge base — pages migrated from the legacy filesystem KB.",
                "network": 2,
                "created_by": owner,
                "updated_by": owner,
                "default_assignee": owner,
            },
        )
        if created:
            ProjectIdentifier.objects.get_or_create(
                workspace=workspace,
                name=KB_PROJECT_IDENTIFIER,
                defaults={"project": project},
            )
            self.stdout.write(self.style.SUCCESS(f"  + created project KB"))

        # Make every workspace member a project member.
        member_user_ids = set(
            ProjectMember.objects.filter(project=project).values_list("member_id", flat=True)
        )
        for ws_member in WorkspaceMember.objects.filter(workspace=workspace):
            if ws_member.member_id in member_user_ids:
                continue
            ProjectMember.objects.create(
                project=project,
                workspace=workspace,
                member=ws_member.member,
                role=ws_member.role,
                created_by=owner,
                updated_by=owner,
            )
        return project

    def _upsert_page(
        self,
        *,
        workspace: Workspace,
        project: Project,
        rel_path: str,
        name: str,
        html: str,
        parent: Page | None,
    ) -> tuple[Page, bool]:
        owner = workspace.owner
        existing = Page.objects.filter(
            workspace=workspace,
            external_id=rel_path,
            external_source="kb-fs",
        ).first()
        created = False
        if existing:
            existing.name = name[:200] or rel_path
            existing.description_html = html
            existing.parent = parent
            existing.save()
            page = existing
        else:
            page = Page.objects.create(
                workspace=workspace,
                name=name[:200] or rel_path,
                description_html=html,
                owned_by=owner,
                access=Page.PUBLIC_ACCESS,
                external_id=rel_path,
                external_source="kb-fs",
                parent=parent,
                created_by=owner,
                updated_by=owner,
            )
            created = True
        ProjectPage.objects.get_or_create(
            project=project,
            page=page,
            defaults={"workspace": workspace},
        )
        return page, created

    def _upload_binary_asset(
        self,
        *,
        workspace: Workspace,
        project: Project,
        page: Page,
        full_path: str,
        rel_path: str,
    ) -> FileAsset | None:
        """Upload a binary file to MinIO and create the FileAsset row.

        Plane stores asset bytes in S3/MinIO out-of-band (the FileAsset
        ``asset`` column just holds the object key) so we use the S3Storage
        ``upload_file`` helper directly instead of going through Django's
        FileField machinery.
        """
        import mimetypes
        import uuid

        from plane.settings.storage import S3Storage

        existing = FileAsset.objects.filter(
            workspace=workspace,
            external_id=rel_path,
            external_source="kb-fs",
        ).first()
        if existing:
            return existing

        try:
            size = os.path.getsize(full_path)
            content_type, _ = mimetypes.guess_type(full_path)
            content_type = content_type or "application/octet-stream"
            object_name = f"{workspace.id}/{uuid.uuid4().hex}-{os.path.basename(full_path)}"

            storage = S3Storage()
            with open(full_path, "rb") as f:
                ok = storage.upload_file(
                    file_obj=f,
                    object_name=object_name,
                    content_type=content_type,
                )
            if not ok:
                self.stderr.write(f"  ! upload_file returned False for {rel_path}")
                return None

            asset = FileAsset.objects.create(
                workspace=workspace,
                project=project,
                page=page,
                asset=object_name,
                attributes={
                    "name": os.path.basename(full_path),
                    "type": content_type,
                    "size": size,
                },
                entity_type=FileAsset.EntityTypeContext.PAGE_DESCRIPTION,
                entity_identifier=str(page.id),
                external_id=rel_path,
                external_source="kb-fs",
                size=size,
                is_uploaded=True,
            )
            return asset
        except Exception as exc:
            self.stderr.write(f"  ! asset upload failed for {rel_path}: {exc}")
            return None

    # ------------------------------------------------------------------ main loop

    def _import_into_workspace(self, workspace: Workspace, *, dry_run: bool):
        if dry_run:
            self.stdout.write("  (dry run)")
            project = None
        else:
            project = self._ensure_kb_project(workspace)

        # Maps relative directory path → Page object (so children can find their parent).
        dir_pages: dict[str, Page] = {}
        stats = {"pages": 0, "updated": 0, "binaries": 0, "skipped": 0}

        # First pass: directories (parents must exist before files).
        for root, dirs, files in os.walk(KB_PATH):
            dirs.sort()
            files.sort()
            rel_root = os.path.relpath(root, KB_PATH)
            if rel_root == ".":
                continue
            if any(part.startswith(".") for part in rel_root.split(os.sep)):
                continue

            parent_rel = os.path.dirname(rel_root)
            parent_page = dir_pages.get(parent_rel) if parent_rel and parent_rel != "." else None

            name = os.path.basename(rel_root).replace("_", " ")
            index_path = os.path.join(root, "_index.md")
            html = ""
            if os.path.isfile(index_path):
                content = _read_text(index_path) or ""
                html = _md_to_html(content)
                name = _title_from_markdown(content, name)

            if dry_run:
                self.stdout.write(f"  dir  {rel_root}")
                stats["pages"] += 1
                continue

            page, created = self._upsert_page(
                workspace=workspace,
                project=project,
                rel_path=rel_root,
                name=name,
                html=html or f"<p><em>Folder: {rel_root}</em></p>",
                parent=parent_page,
            )
            dir_pages[rel_root] = page
            if created:
                stats["pages"] += 1
            else:
                stats["updated"] += 1

        # Second pass: files
        for root, dirs, files in os.walk(KB_PATH):
            dirs.sort()
            files.sort()
            rel_root = os.path.relpath(root, KB_PATH)
            if any(part.startswith(".") for part in (rel_root.split(os.sep) if rel_root != "." else [])):
                continue
            parent_page = dir_pages.get(rel_root) if rel_root != "." else None

            for fname in files:
                if fname.startswith(".") or fname == "_index.md":
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, KB_PATH)
                ext = os.path.splitext(fname)[1].lower()

                if ext in TEXT_EXTS:
                    content = _read_text(full_path) or ""
                    title = _title_from_markdown(content, fname.rsplit(".", 1)[0])
                    html = _md_to_html(content) if ext != ".txt" else f"<pre>{content}</pre>"
                elif ext in BINARY_EXTS:
                    if ext in PDF_EXTS:
                        body = _extract_pdf(full_path)
                    elif ext in DOCX_EXTS:
                        body = _extract_docx(full_path)
                    else:
                        body = ""
                    title = fname.rsplit(".", 1)[0]
                    # Body will be filled in after asset upload (need URL).
                    html = (
                        f"<p><strong>{fname}</strong></p>"
                        + (f"<pre>{body[:5000]}</pre>" if body else "")
                    )
                else:
                    stats["skipped"] += 1
                    continue

                if dry_run:
                    self.stdout.write(f"  file {rel_path}")
                    stats["pages"] += 1
                    continue

                page, created = self._upsert_page(
                    workspace=workspace,
                    project=project,
                    rel_path=rel_path,
                    name=title,
                    html=html,
                    parent=parent_page,
                )
                if created:
                    stats["pages"] += 1
                else:
                    stats["updated"] += 1

                if ext in BINARY_EXTS:
                    asset = self._upload_binary_asset(
                        workspace=workspace,
                        project=project,
                        page=page,
                        full_path=full_path,
                        rel_path=rel_path,
                    )
                    if asset:
                        download_url = asset.asset_url or ""
                        page.description_html += (
                            f'<p><a href="{download_url}" download>Download original {fname}</a></p>'
                        )
                        page.save(update_fields=["description_html", "description_stripped"])
                        stats["binaries"] += 1

        self.stdout.write(self.style.SUCCESS(f"  → pages={stats['pages']} updated={stats['updated']} binaries={stats['binaries']} skipped={stats['skipped']}"))
