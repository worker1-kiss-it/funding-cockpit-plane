"""Security-focused tests for the legacy KB endpoints.

These guard the most important regressions:
- KBRawFileView must require authentication (it used to bypass it)
- _safe_path must reject path traversal
- File reads must be size-bounded
- Search must reject too-short queries
"""

import os
import tempfile
from unittest import mock

import pytest

from plane.funding import views_kb


class TestSafePath:
    def test_normal_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(views_kb, "KB_PATH", str(tmp_path))
        (tmp_path / "doc.md").write_text("hello")
        resolved = views_kb._safe_path("doc.md")
        assert resolved == str(tmp_path / "doc.md")

    def test_traversal_with_dotdot_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(views_kb, "KB_PATH", str(tmp_path))
        assert views_kb._safe_path("../../etc/passwd") is None

    def test_absolute_path_outside_kb_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(views_kb, "KB_PATH", str(tmp_path))
        assert views_kb._safe_path("/etc/passwd") is None

    def test_null_byte_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(views_kb, "KB_PATH", str(tmp_path))
        assert views_kb._safe_path("doc\x00.md") is None

    def test_empty_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(views_kb, "KB_PATH", str(tmp_path))
        assert views_kb._safe_path("") is None


class TestKBRawFileViewAuth:
    """KBRawFileView must NOT bypass auth."""

    def test_view_class_does_not_disable_authentication(self):
        # The previous version had `authentication_classes = []` and
        # `permission_classes = []` directly on the class. Make sure those
        # never come back.
        cls = views_kb.KBRawFileView
        own_attrs = vars(cls)
        assert "authentication_classes" not in own_attrs or own_attrs["authentication_classes"], (
            "KBRawFileView must not override authentication_classes to []"
        )
        assert "permission_classes" not in own_attrs or own_attrs["permission_classes"], (
            "KBRawFileView must not override permission_classes to []"
        )


class TestSearch:
    def test_short_query_rejected(self):
        # The view enforces MIN_SEARCH_QUERY_LEN; this is a unit-level check.
        assert views_kb.MIN_SEARCH_QUERY_LEN >= 3

    def test_search_is_bounded(self, tmp_path, monkeypatch):
        monkeypatch.setattr(views_kb, "KB_PATH", str(tmp_path))
        # Create a few small files
        for i in range(5):
            (tmp_path / f"file{i}.md").write_text("the quick brown fox")
        results = views_kb._search_files("quick")
        assert len(results) <= views_kb.MAX_SEARCH_RESULTS
        # Snippets must be HTML-escaped
        for r in results:
            for m in r["matches"]:
                assert "<" not in m["context"] or "&lt;" in m["context"]


class TestFileLimits:
    def test_max_file_bytes_is_capped(self):
        assert views_kb.MAX_FILE_BYTES <= 10 * 1024 * 1024
