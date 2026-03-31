"""
Create a new tenant (workspace) with the standard funding pipeline setup.

Usage:
  python manage.py create_tenant --name "Company Name" --slug company-name --admin admin@example.com
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from plane.db.models import (
    User,
    Workspace,
    WorkspaceMember,
    Project,
    ProjectMember,
    ProjectIdentifier,
    State,
    Label,
)

FUNDING_PHASES = [
    {"name": "Backlog", "group": "backlog", "color": "#60646C", "sequence": 10000},
    {"name": "Discovery", "group": "unstarted", "color": "#7C8EA6", "sequence": 20000},
    {"name": "Evaluation", "group": "unstarted", "color": "#6B8FD4", "sequence": 30000},
    {"name": "Qualified", "group": "started", "color": "#4EA8DE", "sequence": 40000},
    {"name": "Preparation", "group": "started", "color": "#F59E0B", "sequence": 50000},
    {"name": "Submission", "group": "started", "color": "#F97316", "sequence": 60000},
    {"name": "Submitted", "group": "started", "color": "#8B5CF6", "sequence": 70000},
    {"name": "Review", "group": "started", "color": "#A855F7", "sequence": 80000},
    {"name": "Negotiation", "group": "started", "color": "#EC4899", "sequence": 90000},
    {"name": "Won", "group": "completed", "color": "#22C55E", "sequence": 100000},
    {"name": "Rejected", "group": "cancelled", "color": "#EF4444", "sequence": 110000},
    {"name": "Archived", "group": "cancelled", "color": "#9AA4BC", "sequence": 120000},
]

LABEL_COLORS = {
    "Horizon Europe": "#8B5CF6",
    "Digital Europe": "#3B82F6",
    "Cascade": "#F59E0B",
    "EIC": "#EC4899",
    "MSCA": "#14B8A6",
    "Eurocluster": "#22C55E",
    "National": "#10B981",
    "Other": "#9CA3AF",
}


class Command(BaseCommand):
    help = "Create a new tenant workspace with funding pipeline setup"

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Company/workspace name")
        parser.add_argument("--slug", required=True, help="Workspace slug (URL-friendly)")
        parser.add_argument("--admin", required=True, help="Admin user email")

    def handle(self, *args, **options):
        name = options["name"]
        slug = options["slug"]
        admin_email = options["admin"]

        admin_user = User.objects.filter(email=admin_email).first()
        if not admin_user:
            self.stderr.write(f"User not found: {admin_email}. Create the user first via magic link login.")
            return

        if Workspace.objects.filter(slug=slug).exists():
            self.stderr.write(f"Workspace already exists: {slug}")
            return

        with transaction.atomic():
            workspace = Workspace.objects.create(
                name=name, slug=slug, owner=admin_user
            )
            WorkspaceMember.objects.create(
                workspace=workspace, member=admin_user, role=20
            )

            project = Project.objects.create(
                workspace=workspace,
                identifier="FUND",
                name="EU Funding Pipeline",
                description="Track and manage EU funding opportunities",
                network=2,
                created_by=admin_user,
                updated_by=admin_user,
                default_assignee=admin_user,
            )
            ProjectIdentifier.objects.get_or_create(
                workspace=workspace, name="FUND", defaults={"project": project}
            )
            ProjectMember.objects.create(
                project=project, member=admin_user, workspace=workspace,
                role=20, created_by=admin_user, updated_by=admin_user,
            )

            # Delete default states and create funding pipeline
            State.objects.filter(project=project).delete()
            for phase in FUNDING_PHASES:
                State.objects.create(
                    project=project, workspace=workspace,
                    name=phase["name"], color=phase["color"],
                    group=phase["group"], sequence=phase["sequence"],
                    default=(phase["name"] == "Backlog"),
                    created_by=admin_user, updated_by=admin_user,
                )

            for label_name, color in LABEL_COLORS.items():
                Label.objects.create(
                    project=project, workspace=workspace,
                    name=label_name, color=color,
                    created_by=admin_user, updated_by=admin_user,
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nTenant created!\n"
            f"  Workspace: {name} ({slug})\n"
            f"  Project: EU Funding Pipeline (FUND)\n"
            f"  Admin: {admin_email}\n"
            f"  12 pipeline states + 8 type labels created\n"
            f"  URL: http://46.225.111.79.nip.io:8800/{slug}/projects/"
        ))
