"""
Auto-provision funding defaults for new workspace members.

When a user is added to a workspace that has a funding project (identifier=FUND),
automatically set up:
- Profile with onboarding complete
- Dark mode theme
- Board layout as default
- All saved funding views as favorites
- Sidebar preferences (pin Funding Dashboard + Knowledge Base)
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from plane.db.models import (
    Project,
    WorkspaceMember,
)
from plane.db.models.favorite import UserFavorite
from plane.db.models.project import ProjectMember, ProjectUserProperty
from plane.db.models.user import Profile
from plane.db.models.view import IssueView
from plane.db.models.workspace import WorkspaceUserPreference


@receiver(post_save, sender=WorkspaceMember)
def provision_funding_defaults(sender, instance, created, **kwargs):
    if not created:
        return

    workspace = instance.workspace
    user = instance.member

    # Only apply to workspaces with a FUND project
    try:
        project = Project.objects.get(workspace=workspace, identifier="FUND")
    except Project.DoesNotExist:
        return

    # 1. Ensure profile exists with onboarding done + dark mode
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            "is_onboarded": True,
            "is_tour_completed": True,
            "is_navigation_tour_completed": True,
            "last_workspace_id": workspace.id,
            "theme": {"theme": "dark"},
            "onboarding_step": {
                "profile_complete": True,
                "workspace_create": True,
                "workspace_invite": True,
                "workspace_join": True,
            },
        },
    )
    if not profile.is_onboarded:
        profile.is_onboarded = True
        profile.is_tour_completed = True
        profile.is_navigation_tour_completed = True
        profile.theme = {"theme": "dark"}
        profile.last_workspace_id = workspace.id
        profile.save()

    # 2. Add as project member to FUND and (if it exists) KB
    ProjectMember.objects.get_or_create(
        project=project,
        member=user,
        workspace=workspace,
        defaults={"role": 15, "created_by": user, "updated_by": user},
    )
    kb_project = Project.objects.filter(workspace=workspace, identifier="KB").first()
    if kb_project:
        ProjectMember.objects.get_or_create(
            project=kb_project,
            member=user,
            workspace=workspace,
            defaults={"role": 15, "created_by": user, "updated_by": user},
        )

    # 3. Set board layout as default (excluding archived/rejected)
    from plane.db.models.state import State

    active_state_ids = list(
        State.objects.filter(project=project, deleted_at__isnull=True)
        .exclude(name__in=["Rejected", "Archived"])
        .values_list("id", flat=True)
    )
    active_state_strs = [str(sid) for sid in active_state_ids]

    ProjectUserProperty.objects.get_or_create(
        user=user,
        project=project,
        workspace=workspace,
        defaults={
            "display_filters": {
                "layout": "board",
                "group_by": "state",
                "order_by": "-created_at",
                "type": None,
                "sub_issue": True,
                "show_empty_groups": True,
            },
            "filters": {
                "state": active_state_strs,
            },
            "display_properties": {
                "assignee": True,
                "due_date": True,
                "labels": True,
                "key": True,
                "priority": True,
                "state": True,
                "start_date": True,
            },
            "created_by": user,
            "updated_by": user,
        },
    )

    # 4. Favorite the project
    UserFavorite.objects.get_or_create(
        workspace=workspace,
        user=user,
        entity_type="project",
        entity_identifier=project.id,
        defaults={
            "name": project.name,
            "project": project,
            "created_by": user,
            "updated_by": user,
        },
    )

    # 5. Favorite all saved views in the project
    views = IssueView.objects.filter(workspace=workspace, project=project)
    for view in views:
        UserFavorite.objects.get_or_create(
            workspace=workspace,
            user=user,
            entity_type="view",
            entity_identifier=view.id,
            defaults={
                "name": view.name,
                "project": project,
                "created_by": user,
                "updated_by": user,
            },
        )

    # 6. Pin Funding Dashboard + Knowledge Base in sidebar
    for key, order in [("funding_dashboard", 200000), ("knowledge_base", 210000)]:
        WorkspaceUserPreference.objects.get_or_create(
            user=user,
            workspace=workspace,
            key=key,
            defaults={"is_pinned": True, "sort_order": order},
        )
