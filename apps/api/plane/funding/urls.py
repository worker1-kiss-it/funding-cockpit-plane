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
    CreateLinkedTaskView,
)
from .views_kb import (
    KBTreeView,
    KBFileView,
    KBSearchView,
    KBRawFileView,
    KBDownloadZipView,
)
from .chat.views import ChatSessionsView, ChatMessagesView
from .views_projects import FundingProjectsView

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
    # Knowledge Base
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/kb/tree/",
        KBTreeView.as_view(),
        name="funding-kb-tree",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/kb/file/",
        KBFileView.as_view(),
        name="funding-kb-file",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/kb/file/raw/",
        KBRawFileView.as_view(),
        name="funding-kb-file-raw",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/kb/search/",
        KBSearchView.as_view(),
        name="funding-kb-search",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:opp_id>/kb/download-zip/",
        KBDownloadZipView.as_view(),
        name="funding-kb-download-zip",
    ),
    # AI Chat (claude CLI backed)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/chat/sessions/",
        ChatSessionsView.as_view(),
        name="funding-chat-sessions",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/chat/sessions/<uuid:session_id>/messages/",
        ChatMessagesView.as_view(),
        name="funding-chat-messages",
    ),
    # Projects (from KB _index.md files)
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/kb/projects/",
        FundingProjectsView.as_view(),
        name="funding-projects",
    ),
    # Create linked task
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/create-task/<uuid:issue_id>/",
        CreateLinkedTaskView.as_view(),
        name="funding-create-task",
    ),
]
