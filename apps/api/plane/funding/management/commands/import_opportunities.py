"""
Import all opportunities from the production opportunities.json into Plane.

Creates Issues + FundingOpportunity records with proper state/label mapping.
Idempotent: skips records with existing external_id.
"""

import json
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from plane.db.models import (
    User,
    Workspace,
    Project,
    State,
    Label,
    Issue,
    IssueAssignee,
    IssueLabel,
)
from plane.funding.models import FundingOpportunity, FundingActivityLog


# Normalize 34 type variants into ~10 categories
TYPE_NORMALIZATION = {
    "Horizon Europe": "Horizon Europe",
    "Horizon Europe - CL4 Digital": "Horizon Europe",
    "Horizon Europe - EIC": "EIC",
    "Horizon Europe - IHI JU": "Horizon Europe",
    "Horizon Europe Health": "Horizon Europe",
    "Digital Europe": "Digital Europe",
    "Digital Europe - ECCC": "Digital Europe",
    "Cascade": "Cascade",
    "Cascade Funding": "Cascade",
    "cascade": "Cascade",
    "Cascade / EU Missions": "Cascade",
    "Cascade / CITADEL": "Cascade",
    "Cascade / REINFORCING": "Cascade",
    "Cascade / PartArt4OW": "Cascade",
    "Cascade / RENEW-BOOSTER": "Cascade",
    "Cascade / DIGITAL Europe": "Cascade",
    "Cascade / SoS2LearnDBS": "Cascade",
    "EIT Urban Mobility / Cascade": "Cascade",
    "EDF Cascade": "Cascade",
    "CITADEL / Digital Europe": "Digital Europe",
    "CYSSDE / Digital Europe": "Digital Europe",
    "ELIAS / Digital Europe": "Digital Europe",
    "Eurocluster / Green Grid": "Eurocluster",
    "ERASMUS+": "ERASMUS+",
    "eurohpc": "EuroHPC",
    "eu_ft_portal": "EU Portal",
    "web-scan": "EU Portal",
    "innovate_uk": "Innovate UK",
    "Climate/Energy": "Other",
    "Digital Inclusion": "Other",
    "EU Cross-Border": "Other",
    "Cultural Heritage Value Chain": "Other",
    "Unknown": "Other",
    "task": "Internal Task",
}

LABEL_COLORS = {
    "Horizon Europe": "#8B5CF6",
    "Digital Europe": "#3B82F6",
    "Cascade": "#F59E0B",
    "EIC": "#EC4899",
    "MSCA": "#14B8A6",
    "Eurocluster": "#22C55E",
    "ERASMUS+": "#F97316",
    "EuroHPC": "#6366F1",
    "EU Portal": "#64748B",
    "Innovate UK": "#DC2626",
    "Other": "#9CA3AF",
    "Internal Task": "#475569",
    "National": "#10B981",
}


class Command(BaseCommand):
    help = "Import all opportunities from opportunities.json into Plane"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="/app/kb/opportunities.json",
            help="Path to opportunities.json",
        )
        parser.add_argument(
            "--workspace",
            default="funding-cockpit",
            help="Workspace slug",
        )
        parser.add_argument(
            "--project",
            default="FUND",
            help="Project identifier",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        workspace_slug = options["workspace"]
        project_id = options["project"]
        dry_run = options["dry_run"]

        # Load data
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f"File not found: {file_path}")
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f"Invalid JSON: {e}")
            return

        self.stdout.write(f"Loaded {len(data)} opportunities from {file_path}")

        if dry_run:
            self._dry_run(data)
            return

        with transaction.atomic():
            self._import(data, workspace_slug, project_id)

    def _dry_run(self, data):
        phases = {}
        types = {}
        for item in data:
            p = item.get("phase", "?")
            phases[p] = phases.get(p, 0) + 1
            t = TYPE_NORMALIZATION.get(item.get("type", ""), "Other")
            types[t] = types.get(t, 0) + 1

        self.stdout.write(f"\nPhases: {json.dumps(phases, indent=2)}")
        self.stdout.write(f"\nNormalized types: {json.dumps(types, indent=2)}")
        self.stdout.write(f"\nTotal: {len(data)} items would be imported")

    def _import(self, data, workspace_slug, project_id):
        # Get workspace and project
        try:
            workspace = Workspace.objects.get(slug=workspace_slug)
        except Workspace.DoesNotExist:
            self.stderr.write(f"Workspace not found: {workspace_slug}")
            return

        try:
            project = Project.objects.get(
                workspace=workspace, identifier=project_id
            )
        except Project.DoesNotExist:
            self.stderr.write(f"Project not found: {project_id}")
            return

        # Get admin user
        admin_user = User.objects.filter(
            email="g.kiss@kiss-it.io"
        ).first()
        if not admin_user:
            admin_user = User.objects.first()
            self.stdout.write(
                f"  Using fallback admin: {admin_user.email}"
            )

        # Build user lookup
        user_lookup = {}
        for u in User.objects.all():
            user_lookup[u.email] = u

        # Build state lookup (case-insensitive)
        states = {}
        for s in State.objects.filter(
            project=project, deleted_at__isnull=True
        ):
            states[s.name.lower()] = s
        default_state = states.get("backlog")

        # Ensure labels exist for all normalized types
        labels = {}
        for label_name, color in LABEL_COLORS.items():
            label, _ = Label.objects.get_or_create(
                project=project,
                workspace=workspace,
                name=label_name,
                defaults={
                    "color": color,
                    "created_by": admin_user,
                    "updated_by": admin_user,
                },
            )
            labels[label_name] = label

        # Import opportunities
        created = 0
        skipped = 0
        errors = 0

        for item in data:
            ext_id = item.get("id", "")
            if not ext_id:
                errors += 1
                continue

            # Skip if already imported
            if FundingOpportunity.objects.filter(
                external_id=ext_id
            ).exists():
                skipped += 1
                continue

            # Map phase to state
            phase = item.get("phase", "backlog").lower()
            state = states.get(phase, default_state)

            # Parse deadline
            deadline = None
            deadline_str = item.get("deadline", "")
            if deadline_str:
                try:
                    parts = deadline_str.split("-")
                    deadline = date(
                        int(parts[0]), int(parts[1]), int(parts[2])
                    )
                except (ValueError, IndexError):
                    pass

            # Map priority
            priority = item.get("priority", "medium")
            if priority not in ("urgent", "high", "medium", "low", "none"):
                priority = "medium"

            # Normalize type
            raw_type = item.get("type", "")
            normalized_type = TYPE_NORMALIZATION.get(raw_type, "Other")

            # Build description HTML
            fit_notes = item.get("fit_notes", "")
            budget = item.get("budget", "")
            source = item.get("source", "")
            url = item.get("url", "")
            desc_parts = [f"<p><strong>{ext_id}</strong></p>"]
            if fit_notes:
                desc_parts.append(f"<p>{fit_notes}</p>")
            if budget:
                desc_parts.append(f"<p><strong>Budget:</strong> {budget}</p>")
            if source:
                desc_parts.append(
                    f"<p><strong>Source:</strong> {source}</p>"
                )
            if url:
                desc_parts.append(
                    f'<p><strong>URL:</strong> <a href="{url}">{url}</a></p>'
                )
            description_html = "\n".join(desc_parts)

            try:
                # Create Issue
                issue = Issue.objects.create(
                    project=project,
                    workspace=workspace,
                    name=item.get("name", ext_id),
                    description_html=description_html,
                    state=state,
                    priority=priority,
                    target_date=deadline,
                    created_by=admin_user,
                    updated_by=admin_user,
                )

                # Assign if specified
                assignee_email = item.get("assignee", "")
                if assignee_email and assignee_email in user_lookup:
                    IssueAssignee.objects.create(
                        issue=issue,
                        assignee=user_lookup[assignee_email],
                        project=project,
                        workspace=workspace,
                        created_by=admin_user,
                        updated_by=admin_user,
                    )

                # Add type label
                if normalized_type in labels:
                    IssueLabel.objects.create(
                        issue=issue,
                        label=labels[normalized_type],
                        project=project,
                        workspace=workspace,
                        created_by=admin_user,
                        updated_by=admin_user,
                    )

                # Create FundingOpportunity
                FundingOpportunity.objects.create(
                    issue=issue,
                    external_id=ext_id,
                    opportunity_type=normalized_type,
                    budget=budget,
                    relevance=item.get("relevance", 1),
                    fit_notes=fit_notes,
                    source=source,
                    url=url if url else "",
                    call_id=item.get("call_id", ""),
                    next_step=item.get("next_step", ""),
                    deadline=deadline,
                    linked_docs=item.get("linked_docs", []),
                    tags=item.get("tags", []),
                    created_by=admin_user,
                    updated_by=admin_user,
                )

                # Import activity logs
                for log_entry in item.get("activity_log", [])[:50]:
                    FundingActivityLog.objects.create(
                        opportunity=FundingOpportunity.objects.get(
                            external_id=ext_id
                        ),
                        user_email=log_entry.get("user", "system"),
                        field=log_entry.get("field", ""),
                        old_value=str(log_entry.get("from", "")),
                        new_value=str(log_entry.get("to", "")),
                    )

                created += 1
                if created % 20 == 0:
                    self.stdout.write(f"  Imported {created} so far...")

            except Exception as e:
                errors += 1
                self.stderr.write(
                    f"  Error importing {ext_id}: {e}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nImport complete: {created} created, {skipped} skipped (already exist), {errors} errors"
            )
        )
