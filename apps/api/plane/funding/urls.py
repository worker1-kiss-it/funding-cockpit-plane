from django.urls import path

from .views import (
    FundingPipelineView,
    FundingOpportunityDetailView,
    FundingDashboardView,
    FundingDeadlinesView,
)

urlpatterns = [
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
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/funding/<uuid:pk>/",
        FundingOpportunityDetailView.as_view(),
        name="funding-opportunity-detail",
    ),
]
