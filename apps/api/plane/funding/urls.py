from django.urls import path

from .views import (
    FundingPipelineView,
    FundingOpportunityDetailView,
    FundingDashboardView,
    FundingDeadlinesView,
    ProposalListCreateView,
    ProposalDetailView,
    PartnerListCreateView,
    PartnerDetailView,
    ConsortiumListCreateView,
    ConsortiumDetailView,
    MeetingListCreateView,
    MeetingDetailView,
    MilestoneListCreateView,
    MilestoneDetailView,
)

urlpatterns = [
    # Pipeline & Dashboard
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/pipeline/",
        FundingPipelineView.as_view(),
        name="funding-pipeline",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/dashboard/",
        FundingDashboardView.as_view(),
        name="funding-dashboard",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/deadlines/",
        FundingDeadlinesView.as_view(),
        name="funding-deadlines",
    ),
    # Opportunity detail
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:pk>/",
        FundingOpportunityDetailView.as_view(),
        name="funding-opportunity-detail",
    ),
    # Proposals
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/proposals/",
        ProposalListCreateView.as_view(),
        name="funding-proposals",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/proposals/<uuid:pk>/",
        ProposalDetailView.as_view(),
        name="funding-proposal-detail",
    ),
    # Partners (workspace-scoped)
    path(
        "workspaces/<str:slug>/funding/partners/",
        PartnerListCreateView.as_view(),
        name="funding-partners",
    ),
    path(
        "workspaces/<str:slug>/funding/partners/<uuid:pk>/",
        PartnerDetailView.as_view(),
        name="funding-partner-detail",
    ),
    # Consortium Members
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/consortium/",
        ConsortiumListCreateView.as_view(),
        name="funding-consortium",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/consortium/<uuid:pk>/",
        ConsortiumDetailView.as_view(),
        name="funding-consortium-detail",
    ),
    # Meetings
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/meetings/",
        MeetingListCreateView.as_view(),
        name="funding-meetings",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/meetings/<uuid:pk>/",
        MeetingDetailView.as_view(),
        name="funding-meeting-detail",
    ),
    # Implementation Milestones
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/milestones/",
        MilestoneListCreateView.as_view(),
        name="funding-milestones",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/milestones/<uuid:pk>/",
        MilestoneDetailView.as_view(),
        name="funding-milestone-detail",
    ),
]
