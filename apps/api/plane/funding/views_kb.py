"""Knowledge Base file serving endpoints.

Serves files from a mounted KB directory (read-only volume).
Supports markdown rendering, full-text search, and raw file serving.

NOTE: this is the legacy filesystem-backed KB. It is being superseded by the
Plane native Pages migration (see ``management/commands/import_kb_to_pages.py``).
Once the migration is decommissioned this whole module is deleted.
"""

import html
import io
import mimetypes
import os
import re
import time
import zipfile

import markdown
from django.http import FileResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView

from .models import FundingOpportunity


KB_PATH = os.environ.get("KB_PATH", "/app/kb")

# Hard limits to keep search and file reads bounded.
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB — refuse to inline anything larger
MAX_SEARCH_FILES_SCANNED = 2000
MAX_SEARCH_RESULTS = 20
SEARCH_WALL_CLOCK_SECONDS = 2.0
MIN_SEARCH_QUERY_LEN = 3


def _safe_path(relative_path):
    """Resolve path and ensure it stays within KB_PATH."""
    if not relative_path or "\x00" in relative_path:
        return None
    full_path = os.path.normpath(os.path.join(KB_PATH, relative_path))
    base = os.path.normpath(KB_PATH)
    if full_path != base and not full_path.startswith(base + os.sep):
        return None
    return full_path


def _build_file_tree(path, base_path=None):
    """Build recursive file tree structure."""
    if base_path is None:
        base_path = path

    items = []
    try:
        for item in sorted(os.listdir(path)):
            if item.startswith("."):
                continue
            item_path = os.path.join(path, item)
            relative_path = os.path.relpath(item_path, base_path)
            if os.path.isdir(item_path):
                items.append(
                    {
                        "name": item,
                        "type": "folder",
                        "path": relative_path,
                        "children": _build_file_tree(item_path, base_path)[
                            "items"
                        ],
                    }
                )
            else:
                items.append(
                    {
                        "name": item,
                        "type": "file",
                        "path": relative_path,
                        "size": os.path.getsize(item_path),
                    }
                )
    except PermissionError:
        pass
    return {"items": items}


def _search_files(query):
    """Search for text in .md and .txt files. Bounded in time and result count."""
    results = []
    query_lower = query.lower()
    started = time.monotonic()
    scanned = 0

    for root, _dirs, files in os.walk(KB_PATH):
        for fname in files:
            if not fname.lower().endswith((".md", ".txt")):
                continue
            scanned += 1
            if scanned > MAX_SEARCH_FILES_SCANNED:
                return results
            if time.monotonic() - started > SEARCH_WALL_CLOCK_SECONDS:
                return results
            if len(results) >= MAX_SEARCH_RESULTS:
                return results

            file_path = os.path.join(root, fname)
            try:
                size = os.path.getsize(file_path)
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue

            relative_path = os.path.relpath(file_path, KB_PATH)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError, OSError):
                continue

            if (
                query_lower not in fname.lower()
                and query_lower not in content.lower()
            ):
                continue

            lines = content.split("\n")
            matches = []
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    snippet = "\n".join(lines[start:end])
                    # Escape so the frontend can render snippets safely.
                    matches.append(
                        {"line": i + 1, "context": html.escape(snippet)}
                    )
                    if len(matches) >= 3:
                        break
            results.append({"file": relative_path, "matches": matches})

    return results


class KBTreeView(BaseAPIView):
    """Get KB folder tree structure."""

    def get(self, request, slug, project_id):
        if not os.path.exists(KB_PATH):
            return Response({"items": []})
        return Response(_build_file_tree(KB_PATH))


class KBFileView(BaseAPIView):
    """Get file content, render markdown to HTML."""

    def get(self, request, slug, project_id):
        path = request.query_params.get("path", "")
        if not path:
            return Response(
                {"error": "path parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        full_path = _safe_path(path)
        if not full_path or not os.path.exists(full_path) or not os.path.isfile(full_path):
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            size = os.path.getsize(full_path)
        except OSError:
            return Response(
                {"error": "File not accessible"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if size > MAX_FILE_BYTES:
            return Response(
                {
                    "error": "File too large to inline; use the raw download endpoint",
                    "size": size,
                    "max": MAX_FILE_BYTES,
                },
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        mime_type, _ = mimetypes.guess_type(full_path)

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return Response(
                {
                    "content": None,
                    "mime_type": mime_type or "application/octet-stream",
                    "file_type": "binary",
                    "download_url": (
                        f"/api/funding/workspaces/{slug}/projects/{project_id}"
                        f"/funding/kb/file/raw/?path={path}"
                    ),
                }
            )

        if path.lower().endswith(".md"):
            html_content = markdown.markdown(
                content,
                extensions=[
                    "codehilite",
                    "fenced_code",
                    "tables",
                    "toc",
                ],
            )
            # Rewrite relative <img src="..."> references to the raw-file endpoint
            # so screenshots embedded in markdown render in-place. Absolute URLs
            # (http://, https://, data:) and root-relative paths (/...) are left
            # untouched.
            md_dir = os.path.dirname(path)

            def _rewrite_img(match: "re.Match[str]") -> str:
                src = match.group(2)
                if re.match(r"^(?:[a-z][a-z0-9+\-.]*:|/|#)", src, re.IGNORECASE):
                    return match.group(0)
                resolved = os.path.normpath(os.path.join(md_dir, src)) if md_dir else src
                if resolved.startswith(".."):
                    return match.group(0)  # do not climb out of KB
                from urllib.parse import quote

                raw_url = (
                    f"/api/funding/workspaces/{slug}/projects/{project_id}"
                    f"/funding/kb/file/raw/?path={quote(resolved, safe='/')}"
                )
                return f'<img{match.group(1)}src="{raw_url}"{match.group(3)}'

            html_content = re.sub(
                r"<img([^>]*?)src=\"([^\"]+)\"([^>]*?)>",
                _rewrite_img,
                html_content,
            )
            return Response(
                {
                    "content": html_content,
                    "raw_content": content,
                    "mime_type": "text/html",
                    "file_type": "markdown",
                }
            )

        return Response(
            {
                "content": content,
                "mime_type": mime_type or "text/plain",
                "file_type": "text",
            }
        )


class KBSearchView(BaseAPIView):
    """Search across all .md/.txt files in KB."""

    throttle_scope = "funding_kb_search"

    def get(self, request, slug, project_id):
        q = (request.query_params.get("q", "") or "").strip()
        if len(q) < MIN_SEARCH_QUERY_LEN:
            return Response(
                {"error": f"Query must be at least {MIN_SEARCH_QUERY_LEN} characters"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Strip control characters; keep things plain.
        q = re.sub(r"[\x00-\x1f\x7f]", "", q)[:200]
        results = _search_files(q)
        return Response(
            {"query": q, "results": results, "total": len(results)}
        )


class KBRawFileView(BaseAPIView):
    """Serve raw files (PDF/images) for viewing/download.

    Authenticated like every other funding endpoint — the previous version
    bypassed auth entirely, allowing anyone who guessed a path to exfiltrate
    files. The frontend must include credentials when fetching raw files
    (use ``fetch(url, { credentials: "include" })`` and create a blob URL).
    """

    throttle_scope = "funding_kb_raw"

    def get(self, request, slug, project_id):
        path = request.query_params.get("path", "")
        if not path:
            return Response(
                {"error": "path parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        full_path = _safe_path(path)
        if not full_path or not os.path.exists(full_path) or not os.path.isfile(full_path):
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        mime_type, _ = mimetypes.guess_type(full_path)
        return FileResponse(
            open(full_path, "rb"),
            content_type=mime_type or "application/octet-stream",
        )


# Per-folder ZIP-download cap. The KB call folder for the EDITO bid is ~70 MB
# of mostly PDFs + screenshots; we set a generous ceiling and refuse anything
# above it to keep memory bounded under the in-memory ZIP path.
MAX_ZIP_BYTES = 200 * 1024 * 1024  # 200 MB
MAX_ZIP_FILES = 5000


def _resolve_opportunity_kb_folder(opportunity):
    """Return the absolute KB folder corresponding to this opportunity.

    Strategy: look at ``linked_docs``. The funding cockpit stores per-call
    artefact paths like ``09_Call_Artifacts/<slug>/<filename>``. The folder
    we want to ZIP is the **common parent directory** of those paths.

    If ``linked_docs`` is empty or points to inconsistent locations, return
    None — the caller surfaces a 404 to the UI rather than guessing.
    """
    paths = [p for p in (opportunity.linked_docs or []) if isinstance(p, str)]
    if not paths:
        return None

    parents = set()
    for p in paths:
        # Drop any trailing filename component to get the directory.
        directory = os.path.dirname(p) or ""
        parents.add(directory)

    if not parents:
        return None

    # Pick the deepest common prefix among the parent directories.
    prefix = os.path.commonpath(list(parents)) if len(parents) > 1 else next(iter(parents))
    if not prefix:
        return None

    full_path = _safe_path(prefix)
    if not full_path or not os.path.isdir(full_path):
        return None
    return full_path


def _zip_directory_to_bytes(folder_path):
    """Build a ZIP archive of folder_path in memory and return BytesIO + size.

    Bounded by MAX_ZIP_BYTES + MAX_ZIP_FILES; raises ValueError if exceeded.
    Uses ZIP_DEFLATED so PDFs and other already-compressed inputs still package
    cleanly (deflate is a no-op on incompressible data; minimal CPU cost).
    """
    buf = io.BytesIO()
    file_count = 0
    bytes_written = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        base = os.path.normpath(folder_path)
        for root, dirs, files in os.walk(base):
            # Skip dot-directories (e.g. .git, .DS_Store-bearing dirs).
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if filename.startswith("."):
                    continue
                file_count += 1
                if file_count > MAX_ZIP_FILES:
                    raise ValueError(
                        f"Folder contains more than {MAX_ZIP_FILES} files; refusing to ZIP."
                    )
                file_path = os.path.join(root, filename)
                # Skip symlinks / non-files defensively.
                if not os.path.isfile(file_path):
                    continue
                try:
                    file_size = os.path.getsize(file_path)
                except OSError:
                    continue
                bytes_written += file_size
                if bytes_written > MAX_ZIP_BYTES:
                    raise ValueError(
                        f"Folder exceeds {MAX_ZIP_BYTES} bytes; refusing to ZIP."
                    )
                arcname = os.path.relpath(file_path, base)
                zf.write(file_path, arcname=arcname)
    buf.seek(0)
    return buf, file_count, bytes_written


class KBDownloadZipView(BaseAPIView):
    """Stream a ZIP archive of an opportunity's KB folder.

    Resolves the per-opportunity folder from ``linked_docs``, walks that
    directory under KB_PATH, and returns a single ZIP. Inherits standard
    Plane authentication via BaseAPIView; no auth bypass.
    """

    throttle_scope = "funding_kb_download_zip"

    def get(self, request, slug, project_id, opp_id):
        opportunity = FundingOpportunity.objects.filter(pk=opp_id).first()
        if not opportunity:
            return Response(
                {"error": "Opportunity not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        folder_path = _resolve_opportunity_kb_folder(opportunity)
        if not folder_path:
            return Response(
                {
                    "error": (
                        "No KB folder is linked to this opportunity. "
                        "Add at least one entry under linked_docs to enable bulk download."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            buf, file_count, bytes_written = _zip_directory_to_bytes(folder_path)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Sanitise filename: strip path separators and clamp length.
        folder_name = os.path.basename(os.path.normpath(folder_path)) or "kb"
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", folder_name)[:120]
        download_name = f"{safe_name}.zip"

        response = StreamingHttpResponse(
            buf,
            content_type="application/zip",
        )
        response["Content-Disposition"] = f'attachment; filename="{download_name}"'
        response["Content-Length"] = str(buf.getbuffer().nbytes)
        response["X-KB-File-Count"] = str(file_count)
        response["X-KB-Uncompressed-Bytes"] = str(bytes_written)
        return response
