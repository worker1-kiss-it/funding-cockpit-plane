"""Background tasks for the funding extension.

The main task here is ``dump_pages_for_chat``: it materialises every Plane
page (limited to projects we want the chat assistant to see) as a markdown
file under ``PAGES_CACHE_PATH``. The local ``claude`` CLI is then pointed at
that directory via ``--add-dir``, giving the assistant searchable, file-shaped
access to the wiki without exposing the database.
"""

from __future__ import annotations

import os
import re

from celery import shared_task
from django.utils import timezone

from html.parser import HTMLParser

from plane.db.models import Page

PAGES_CACHE_PATH = os.environ.get("PAGES_CACHE_PATH", "/app/pages-cache")


class _HTMLToText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def _html_to_markdown(html: str) -> str:
    # Plane stores rich content as HTML; for the chat cache we keep it lo-fi
    # (no need to round-trip to perfect markdown — the assistant just needs
    # the words).
    parser = _HTMLToText()
    try:
        parser.feed(html or "")
    except Exception:
        return html or ""
    text = parser.text()
    # Collapse runs of blank lines.
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "page").strip("-")
    return value[:80] or "page"


@shared_task(name="plane.funding.dump_pages_for_chat")
def dump_pages_for_chat(force: bool = False):
    """Dump every page (workspace + project scoped) to disk as markdown.

    Re-dumps a page only if its ``updated_at`` is newer than the cached file's
    mtime, unless ``force`` is True. Returns a small report dict.
    """
    os.makedirs(PAGES_CACHE_PATH, exist_ok=True)
    written = skipped = 0

    qs = Page.objects.select_related("workspace").prefetch_related("projects")
    for page in qs.iterator(chunk_size=200):
        workspace_slug = page.workspace.slug
        project_slugs = [p.identifier for p in page.projects.all()] or ["_workspace"]
        for project_slug in project_slugs:
            out_dir = os.path.join(PAGES_CACHE_PATH, workspace_slug, project_slug)
            os.makedirs(out_dir, exist_ok=True)
            filename = f"{_slugify(page.name)}-{str(page.id)[:8]}.md"
            out_path = os.path.join(out_dir, filename)

            if not force and os.path.exists(out_path):
                try:
                    cached_mtime = os.path.getmtime(out_path)
                    if page.updated_at.timestamp() <= cached_mtime:
                        skipped += 1
                        continue
                except OSError:
                    pass

            body = _html_to_markdown(page.description_html or "")
            front = f"# {page.name}\n\n_Page id: {page.id}_\n\n"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(front + body + "\n")
            written += 1

    return {
        "written": written,
        "skipped": skipped,
        "ts": timezone.now().isoformat(),
        "path": PAGES_CACHE_PATH,
    }
