"""
Seed the database with funding cockpit data:
- Creates users (with magic link auth - no password needed)
- Creates workspace "Funding Cockpit"
- Creates project "EU Funding Pipeline" with custom states matching the 12-phase pipeline
- Creates labels for opportunity types
- Creates issues representing sample funding opportunities
- Creates FundingOpportunity records with metadata
"""

import uuid
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from plane.db.models import (
    User,
    Workspace,
    WorkspaceMember,
    Project,
    ProjectMember,
    ProjectIdentifier,
    State,
    Label,
    Issue,
    IssueAssignee,
    IssueLabel,
)
from plane.db.models.user import Profile
from plane.funding.models import FundingOpportunity, FundingActivityLog


# Funding pipeline phases mapped to Plane state groups
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

OPPORTUNITY_TYPES = [
    {"name": "Cascade", "color": "#3B82F6"},
    {"name": "Horizon", "color": "#8B5CF6"},
    {"name": "MSCA", "color": "#EC4899"},
    {"name": "EIC", "color": "#F59E0B"},
    {"name": "National", "color": "#22C55E"},
]

SAMPLE_OPPORTUNITIES = [
    {
        "external_id": "CASCADE-001",
        "name": "COP-PILOT 1st Open Call",
        "type": "Cascade",
        "deadline": "2026-04-17",
        "budget": "€200,000",
        "phase": "Discovery",
        "relevance": 3,
        "priority": "medium",
        "fit_notes": "Cloud-Edge-IoT, needs SME with IoT experience. Good fit but need pilot partner.",
        "source": "Shafi email #002",
        "url": "https://cascadefunding.eu/open-calls/",
    },
    {
        "external_id": "CASCADE-002",
        "name": "CYberSynchrony",
        "type": "Cascade",
        "deadline": "2026-05-01",
        "budget": "€60,000",
        "phase": "Evaluation",
        "relevance": 4,
        "priority": "high",
        "fit_notes": "Cybersecurity focus, perfect fit for KISS IT core competency. Strong alignment with our expertise.",
        "source": "Shafi email #004",
    },
    {
        "external_id": "CASCADE-003",
        "name": "ECIV 1st Open Call",
        "type": "Cascade",
        "deadline": "2026-05-01",
        "budget": "€60,000",
        "phase": "Discovery",
        "relevance": 3,
        "priority": "medium",
        "fit_notes": "Digital innovation vouchers. Good for capacity building but limited direct technical fit.",
        "source": "Shafi email #005",
    },
    {
        "external_id": "HORIZON-001",
        "name": "Horizon Top Pick 8 - GenAI-Cybersecure EU",
        "type": "Horizon",
        "deadline": "2026-09-01",
        "budget": "€3-5M (consortium)",
        "phase": "Preparation",
        "relevance": 5,
        "priority": "urgent",
        "fit_notes": "AI + cybersecurity = our core competency. Excellent fit, this is our sweet spot. High priority.",
        "source": "Shafi emails analysis",
        "assignee_email": "g.kiss@kiss-it.io",
    },
    {
        "external_id": "WEBINAR-SECURE",
        "name": "SECURE (CRA for SMEs)",
        "type": "Cascade",
        "deadline": "2026-03-31",
        "budget": "€30,000",
        "phase": "Submission",
        "relevance": 4,
        "priority": "urgent",
        "fit_notes": "CRA compliance for SMEs, 50% co-funding. Direct relevance to our compliance consulting services.",
        "source": "Webinar Info Day #29",
        "url": "https://www.secure4sme.eu",
        "assignee_email": "g.kiss@kiss-it.io",
    },
    {
        "external_id": "MSCA-PQC-2024",
        "name": "Post-Quantum Cryptography Fellowship",
        "type": "MSCA",
        "deadline": "2026-03-15",
        "budget": "€180,000",
        "phase": "Review",
        "relevance": 5,
        "priority": "high",
        "fit_notes": "Individual fellowship for PQC research. Submitted with University of Vienna partnership.",
        "source": "Direct application",
        "assignee_email": "r.hasan@kiss-it.io",
    },
    {
        "external_id": "HORIZON-009",
        "name": "SW/HW Security Development & Assessment (ECCC 2026)",
        "type": "Horizon",
        "deadline": "2026-09-15",
        "budget": "€3-5M (consortium)",
        "phase": "Discovery",
        "relevance": 4,
        "priority": "medium",
        "fit_notes": "CRA-aligned secure development tools. Strong fit via SECURE project experience. DevSecOps + supply chain security.",
        "source": "Euresearch / Shafi referral",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
    },
    {
        "external_id": "HORIZON-010",
        "name": "SecureAI - AI Security Privacy Robustness (ECCC 2026)",
        "type": "Horizon",
        "deadline": "2026-09-15",
        "budget": "€3-5M (consortium)",
        "phase": "Discovery",
        "relevance": 5,
        "priority": "urgent",
        "fit_notes": "TOP PICK. AI + cybersecurity = our core. MLSecOps, adversarial ML, AI Act compliance. Best fit of all ECCC calls.",
        "source": "Euresearch / Shafi referral",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
        "assignee_email": "g.kiss@kiss-it.io",
    },
    {
        "external_id": "HORIZON-011",
        "name": "Advanced Cryptography & High-Assurance Crypto (ECCC 2026)",
        "type": "Horizon",
        "deadline": "2026-09-15",
        "budget": "€3-5M (consortium)",
        "phase": "Discovery",
        "relevance": 4,
        "priority": "medium",
        "fit_notes": "PQC + DeFi crypto migration angle. Leverage University of Vienna PQC fellowship. ZKP applications.",
        "source": "Euresearch / Shafi referral",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
    },
]


class Command(BaseCommand):
    help = "Seed the database with funding cockpit data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding funding cockpit data...")

        with transaction.atomic():
            # 1. Create users
            users = {}
            for email, display_name in [
                ("g.kiss@kiss-it.io", "Gergely Kiss"),
                ("r.hasan@kiss-it.io", "Rafi Hasan"),
                ("shafi@mediprospects.ai", "Shafi Ahmed"),
            ]:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": email,
                        "display_name": display_name,
                        "is_active": True,
                        "is_password_autoset": True,
                    },
                )
                if created:
                    self.stdout.write(f"  Created user: {email}")
                else:
                    self.stdout.write(f"  User exists: {email}")
                users[email] = user

            admin_user = users["g.kiss@kiss-it.io"]

            # 1b. Create profiles (skip onboarding/profile setup screen)
            for email, user in users.items():
                Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        "is_onboarded": True,
                        "is_tour_completed": True,
                        "is_navigation_tour_completed": True,
                        "onboarding_step": {
                            "profile_complete": True,
                            "workspace_create": True,
                            "workspace_invite": True,
                            "workspace_join": True,
                        },
                    },
                )

            # 2. Create workspace
            workspace, created = Workspace.objects.get_or_create(
                slug="funding-cockpit",
                defaults={
                    "name": "Funding Cockpit",
                    "owner": admin_user,
                },
            )
            if created:
                self.stdout.write("  Created workspace: Funding Cockpit")
            else:
                self.stdout.write("  Workspace exists: Funding Cockpit")

            # 3. Add all users as workspace members
            for email, user in users.items():
                WorkspaceMember.objects.get_or_create(
                    workspace=workspace,
                    member=user,
                    defaults={"role": 20},  # 20 = Admin
                )

            # 4. Create project
            project, created = Project.objects.get_or_create(
                workspace=workspace,
                identifier="FUND",
                defaults={
                    "name": "EU Funding Pipeline",
                    "description": "Track and manage EU funding opportunities - Horizon Europe, Cascade, EIC, MSCA, and other programs",
                    "network": 2,  # Secret
                    "created_by": admin_user,
                    "updated_by": admin_user,
                    "default_assignee": admin_user,
                },
            )
            if created:
                self.stdout.write("  Created project: EU Funding Pipeline")

                # Create project identifier
                ProjectIdentifier.objects.get_or_create(
                    workspace=workspace,
                    name="FUND",
                    defaults={"project": project},
                )

            # 5. Add users as project members
            for email, user in users.items():
                ProjectMember.objects.get_or_create(
                    project=project,
                    member=user,
                    workspace=workspace,
                    defaults={
                        "role": 20,
                        "created_by": admin_user,
                        "updated_by": admin_user,
                    },
                )

            # 6. Create funding pipeline states (delete defaults first if project was just created)
            if created:
                State.objects.filter(project=project).delete()

            states = {}
            default_set = False
            for phase in FUNDING_PHASES:
                state, _ = State.objects.get_or_create(
                    project=project,
                    workspace=workspace,
                    name=phase["name"],
                    defaults={
                        "color": phase["color"],
                        "group": phase["group"],
                        "sequence": phase["sequence"],
                        "default": not default_set and phase["name"] == "Backlog",
                        "created_by": admin_user,
                        "updated_by": admin_user,
                    },
                )
                if phase["name"] == "Backlog":
                    default_set = True
                states[phase["name"]] = state

            self.stdout.write(f"  Created {len(states)} pipeline states")

            # 7. Create labels for opportunity types
            labels = {}
            for label_data in OPPORTUNITY_TYPES:
                label, _ = Label.objects.get_or_create(
                    project=project,
                    workspace=workspace,
                    name=label_data["name"],
                    defaults={
                        "color": label_data["color"],
                        "created_by": admin_user,
                        "updated_by": admin_user,
                    },
                )
                labels[label_data["name"]] = label

            self.stdout.write(f"  Created {len(labels)} opportunity type labels")

            # 8. Create issues + FundingOpportunity records
            issue_count = 0
            for opp_data in SAMPLE_OPPORTUNITIES:
                # Check if already exists
                if FundingOpportunity.objects.filter(
                    external_id=opp_data["external_id"]
                ).exists():
                    self.stdout.write(
                        f"  Opportunity exists: {opp_data['external_id']}"
                    )
                    continue

                state = states.get(opp_data["phase"], states["Backlog"])
                deadline = None
                if opp_data.get("deadline"):
                    parts = opp_data["deadline"].split("-")
                    deadline = date(int(parts[0]), int(parts[1]), int(parts[2]))

                issue = Issue.objects.create(
                    project=project,
                    workspace=workspace,
                    name=opp_data["name"],
                    description_html=f"<p><strong>{opp_data['external_id']}</strong>: {opp_data.get('fit_notes', '')}</p><p>Budget: {opp_data.get('budget', 'TBD')}</p><p>Source: {opp_data.get('source', '')}</p>",
                    state=state,
                    priority=opp_data.get("priority", "medium"),
                    target_date=deadline,
                    created_by=admin_user,
                    updated_by=admin_user,
                )

                # Assign if specified
                assignee_email = opp_data.get("assignee_email")
                if assignee_email and assignee_email in users:
                    IssueAssignee.objects.create(
                        issue=issue,
                        assignee=users[assignee_email],
                        project=project,
                        workspace=workspace,
                        created_by=admin_user,
                        updated_by=admin_user,
                    )

                # Add type label
                if opp_data.get("type") and opp_data["type"] in labels:
                    IssueLabel.objects.create(
                        issue=issue,
                        label=labels[opp_data["type"]],
                        project=project,
                        workspace=workspace,
                        created_by=admin_user,
                        updated_by=admin_user,
                    )

                # Create FundingOpportunity
                FundingOpportunity.objects.create(
                    issue=issue,
                    external_id=opp_data["external_id"],
                    opportunity_type=opp_data.get("type", ""),
                    budget=opp_data.get("budget", ""),
                    relevance=opp_data.get("relevance", 1),
                    fit_notes=opp_data.get("fit_notes", ""),
                    source=opp_data.get("source", ""),
                    url=opp_data.get("url", ""),
                    deadline=deadline,
                    created_by=admin_user,
                    updated_by=admin_user,
                )

                issue_count += 1
                self.stdout.write(
                    f"  Created: {opp_data['external_id']} - {opp_data['name']} [{opp_data['phase']}]"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone! Created {issue_count} funding opportunities.\n"
                    f"Workspace: funding-cockpit\n"
                    f"Project: EU Funding Pipeline (FUND)\n"
                    f"Users: g.kiss@kiss-it.io, r.hasan@kiss-it.io, shafi@mediprospects.ai\n"
                    f"Login via magic link (email code) - no passwords needed."
                )
            )
