"""Knowledge Base file serving endpoints.

Serves files from a mounted KB directory (read-only volume).
Supports markdown rendering, full-text search, and raw file serving.
"""

import os
import mimetypes

import markdown
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView


KB_PATH = os.environ.get("KB_PATH", "/app/kb")


def _safe_path(relative_path):
    """Resolve path and ensure it stays within KB_PATH."""
    full_path = os.path.normpath(os.path.join(KB_PATH, relative_path))
    if not full_path.startswith(os.path.normpath(KB_PATH)):
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
    """Search for text in .md and .txt files."""
    results = []
    query_lower = query.lower()

    for root, dirs, files in os.walk(KB_PATH):
        for fname in files:
            if not fname.lower().endswith((".md", ".txt")):
                continue
            file_path = os.path.join(root, fname)
            relative_path = os.path.relpath(file_path, KB_PATH)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if query_lower not in fname.lower() and query_lower not in content.lower():
                    continue
                lines = content.split("\n")
                matches = []
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = "\n".join(lines[start:end])
                        matches.append({"line": i + 1, "context": context})
                results.append(
                    {
                        "file": relative_path,
                        "matches": matches[:3],
                    }
                )
            except (UnicodeDecodeError, PermissionError):
                continue
    return results[:20]


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
        if not full_path or not os.path.exists(full_path):
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
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
                    "download_url": f"/api/funding/workspaces/{slug}/projects/{project_id}/funding/kb/file/raw/?path={path}",
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

    def get(self, request, slug, project_id):
        q = request.query_params.get("q", "")
        if len(q) < 2:
            return Response(
                {"error": "Query must be at least 2 characters"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        results = _search_files(q)
        return Response(
            {"query": q, "results": results, "total": len(results)}
        )


class KBRawFileView(BaseAPIView):
    """Serve raw files (PDF/images) for viewing/download."""

    authentication_classes = []
    permission_classes = []

    def get(self, request, slug, project_id):
        path = request.query_params.get("path", "")
        if not path:
            return Response(
                {"error": "path parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        full_path = _safe_path(path)
        if not full_path or not os.path.exists(full_path):
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        mime_type, _ = mimetypes.guess_type(full_path)
        return FileResponse(
            open(full_path, "rb"),
            content_type=mime_type or "application/octet-stream",
        )
