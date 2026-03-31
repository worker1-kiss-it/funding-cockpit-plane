"""Projects view — scans KB for _index.md files and extracts metadata.

Parses project information from the knowledge base directory structure
where each project subdirectory contains an _index.md with metadata.
"""

import os
import re

from rest_framework.response import Response

from plane.app.views.base import BaseAPIView


KB_PATH = os.environ.get("KB_PATH", "/app/kb")


def _parse_index_file(file_path):
    """Parse _index.md and extract project metadata."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    # Parent directory is the project name
    parts = file_path.split(os.sep)
    name = parts[-2] if len(parts) >= 2 else "Unknown"

    project = {
        "name": name,
        "relevance": 0,
        "call_id": "",
        "has_proposal": False,
        "has_esr": False,
        "content": content,
        "path": os.path.relpath(file_path, KB_PATH),
    }

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("#") and not project.get("title"):
            project["title"] = line.lstrip("#").strip()

        stars_match = re.search(r"(\*{1,5}|⭐{1,5}|[0-5]/5)", line)
        if stars_match:
            stars = stars_match.group(1)
            if "*" in stars:
                project["relevance"] = len(stars)
            elif "⭐" in stars:
                project["relevance"] = len(stars)
            elif "/" in stars:
                project["relevance"] = int(stars.split("/")[0])

        call_match = re.search(
            r"call[\s-]*id[\s:]*([A-Z0-9-]+)", line, re.IGNORECASE
        )
        if call_match:
            project["call_id"] = call_match.group(1)

    dir_path = os.path.dirname(file_path)
    try:
        for fname in os.listdir(dir_path):
            if "proposal" in fname.lower():
                project["has_proposal"] = True
            if "esr" in fname.lower():
                project["has_esr"] = True
    except OSError:
        pass

    return project


def _get_project_category(file_path):
    path_lower = file_path.lower()
    if "01_projects/full_match" in path_lower:
        return "Full Match"
    elif "01_projects/esr_only" in path_lower:
        return "ESR Only"
    elif "01_projects/proposal_only" in path_lower:
        return "Proposal Only"
    elif "02_our_submissions" in path_lower:
        return "Our Submissions"
    return "Other"


def _find_all_projects():
    projects = []
    for root, dirs, files in os.walk(KB_PATH):
        for fname in files:
            if fname == "_index.md":
                file_path = os.path.join(root, fname)
                project = _parse_index_file(file_path)
                if project:
                    project["category"] = _get_project_category(file_path)
                    projects.append(project)
    projects.sort(key=lambda x: (-x["relevance"], x["name"]))
    return projects


class FundingProjectsView(BaseAPIView):
    """Get all projects from _index.md files in the KB."""

    def get(self, request, slug, project_id):
        projects = _find_all_projects()
        by_category = {}
        for p in projects:
            cat = p["category"]
            by_category.setdefault(cat, []).append(p)
        return Response(
            {
                "projects": projects,
                "by_category": by_category,
                "total": len(projects),
            }
        )
