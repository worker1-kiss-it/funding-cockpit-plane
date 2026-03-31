from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Count, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.db.models import Issue, State, Project, Workspace

from .models import (
    FundingOpportunity,
    FundingActivityLog,
    Proposal,
    Partner,
    ConsortiumMember,
    Meeting,
    ImplementationMilestone,
)
from .serializers import (
    FundingOpportunitySerializer,
    FundingOpportunityUpdateSerializer,
    ProposalSerializer,
    PartnerSerializer,
    ConsortiumMemberSerializer,
    MeetingSerializer,
    ImplementationMilestoneSerializer,
)


# ---------------------------------------------------------------------------
# Funding Pipeline & Dashboard
# ---------------------------------------------------------------------------


class FundingPipelineView(BaseAPIView):
    """Get all funding opportunities grouped by phase/state."""

    def get(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        opportunities = (
            FundingOpportunity.objects.filter(
                issue__project=project,
                issue__deleted_at__isnull=True,
            )
            .select_related("issue", "issue__state")
            .prefetch_related("issue__assignees", "activity_logs")
            .order_by("issue__state__sequence", "-relevance")
        )

        serializer = FundingOpportunitySerializer(opportunities, many=True)

        by_phase = defaultdict(list)
        for item in serializer.data:
            phase = item.get("issue_state", "Backlog")
            by_phase[phase].append(item)

        states = list(
            State.objects.filter(project=project, deleted_at__isnull=True)
            .exclude(group="triage")
            .order_by("sequence")
            .values_list("name", flat=True)
        )

        return Response(
            {
                "opportunities": serializer.data,
                "by_phase": dict(by_phase),
                "phases": states,
                "total": len(serializer.data),
            }
        )


class FundingOpportunityDetailView(BaseAPIView):
    """Get/update a single funding opportunity."""

    def get(self, request, slug, project_id, pk):
        opportunity = (
            FundingOpportunity.objects.filter(
                pk=pk,
                issue__project_id=project_id,
                issue__workspace__slug=slug,
            )
            .select_related("issue", "issue__state")
            .prefetch_related(
                "issue__assignees",
                "activity_logs",
                "proposals",
                "consortium_members",
                "consortium_members__partner",
                "meetings",
                "milestones",
            )
            .first()
        )
        if not opportunity:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = FundingOpportunitySerializer(opportunity)
        return Response(serializer.data)

    def patch(self, request, slug, project_id, pk):
        opportunity = FundingOpportunity.objects.filter(
            pk=pk,
            issue__project_id=project_id,
            issue__workspace__slug=slug,
        ).first()
        if not opportunity:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_email = request.user.email
        for field in ["relevance", "fit_notes", "next_step", "budget"]:
            if field in request.data:
                old_val = str(getattr(opportunity, field, ""))
                new_val = str(request.data[field])
                if old_val != new_val:
                    FundingActivityLog.objects.create(
                        opportunity=opportunity,
                        user_email=user_email,
                        field=field,
                        old_value=old_val,
                        new_value=new_val,
                    )

        serializer = FundingOpportunityUpdateSerializer(
            opportunity, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(FundingOpportunitySerializer(opportunity).data)


class FundingDashboardView(BaseAPIView):
    """Dashboard stats for the funding cockpit."""

    def get(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        opportunities = FundingOpportunity.objects.filter(
            issue__project=project,
            issue__deleted_at__isnull=True,
        ).select_related("issue", "issue__state")

        today = date.today()
        month_end = today.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        week_from_now = today + timedelta(days=7)

        total = opportunities.count()
        by_type = defaultdict(int)
        high_priority = 0
        deadlines_this_month = 0
        urgent_deadlines = 0

        for opp in opportunities:
            by_type[opp.opportunity_type] += 1
            if opp.relevance >= 4:
                high_priority += 1
            if opp.deadline:
                if opp.deadline <= month_end:
                    deadlines_this_month += 1
                if opp.deadline <= week_from_now:
                    urgent_deadlines += 1

        by_phase = defaultdict(int)
        for opp in opportunities:
            state_name = (
                opp.issue.state.name if opp.issue.state else "Unknown"
            )
            by_phase[state_name] += 1

        return Response(
            {
                "total_opportunities": total,
                "by_phase": dict(by_phase),
                "by_type": dict(by_type),
                "high_priority": high_priority,
                "deadlines_this_month": deadlines_this_month,
                "urgent_deadlines": urgent_deadlines,
            }
        )


class FundingDeadlinesView(BaseAPIView):
    """Get upcoming deadlines for calendar view."""

    def get(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        opportunities = (
            FundingOpportunity.objects.filter(
                issue__project=project,
                issue__deleted_at__isnull=True,
                deadline__isnull=False,
            )
            .select_related("issue", "issue__state")
            .order_by("deadline")
        )

        today = date.today()
        deadlines = []
        for opp in opportunities:
            days_left = (opp.deadline - today).days
            if days_left < 7:
                urgency = "red"
            elif days_left < 30:
                urgency = "yellow"
            else:
                urgency = "green"

            deadlines.append(
                {
                    "id": str(opp.id),
                    "external_id": opp.external_id,
                    "name": opp.issue.name,
                    "deadline": opp.deadline.isoformat(),
                    "days_left": days_left,
                    "urgency": urgency,
                    "budget": opp.budget,
                    "phase": (
                        opp.issue.state.name if opp.issue.state else ""
                    ),
                    "relevance": opp.relevance,
                    "opportunity_type": opp.opportunity_type,
                }
            )

        return Response(
            {"deadlines": deadlines, "total": len(deadlines)}
        )


# ---------------------------------------------------------------------------
# Proposal CRUD
# ---------------------------------------------------------------------------


class ProposalListCreateView(BaseAPIView):
    def get(self, request, slug, project_id, opp_id):
        proposals = Proposal.objects.filter(
            opportunity_id=opp_id,
            opportunity__issue__project_id=project_id,
            opportunity__issue__workspace__slug=slug,
        ).order_by("-created_at")
        return Response(ProposalSerializer(proposals, many=True).data)

    def post(self, request, slug, project_id, opp_id):
        opportunity = FundingOpportunity.objects.filter(
            pk=opp_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug,
        ).first()
        if not opportunity:
            return Response(
                {"error": "Opportunity not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(opportunity=opportunity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProposalDetailView(BaseAPIView):
    def get(self, request, slug, project_id, opp_id, pk):
        proposal = Proposal.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not proposal:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(ProposalSerializer(proposal).data)

    def patch(self, request, slug, project_id, opp_id, pk):
        proposal = Proposal.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not proposal:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProposalSerializer(
            proposal, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug, project_id, opp_id, pk):
        proposal = Proposal.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not proposal:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        proposal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Partner CRUD (workspace-scoped)
# ---------------------------------------------------------------------------


class PartnerListCreateView(BaseAPIView):
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        partners = Partner.objects.filter(
            workspace=workspace, deleted_at__isnull=True
        )
        return Response(PartnerSerializer(partners, many=True).data)

    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = PartnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(workspace=workspace)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PartnerDetailView(BaseAPIView):
    def get(self, request, slug, pk):
        partner = Partner.objects.filter(
            pk=pk, workspace__slug=slug
        ).first()
        if not partner:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(PartnerSerializer(partner).data)

    def patch(self, request, slug, pk):
        partner = Partner.objects.filter(
            pk=pk, workspace__slug=slug
        ).first()
        if not partner:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = PartnerSerializer(
            partner, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug, pk):
        partner = Partner.objects.filter(
            pk=pk, workspace__slug=slug
        ).first()
        if not partner:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        partner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Consortium Member CRUD
# ---------------------------------------------------------------------------


class ConsortiumListCreateView(BaseAPIView):
    def get(self, request, slug, project_id, opp_id):
        members = ConsortiumMember.objects.filter(
            opportunity_id=opp_id,
            opportunity__issue__project_id=project_id,
            opportunity__issue__workspace__slug=slug,
        ).select_related("partner")
        return Response(
            ConsortiumMemberSerializer(members, many=True).data
        )

    def post(self, request, slug, project_id, opp_id):
        opportunity = FundingOpportunity.objects.filter(
            pk=opp_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug,
        ).first()
        if not opportunity:
            return Response(
                {"error": "Opportunity not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ConsortiumMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(opportunity=opportunity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConsortiumDetailView(BaseAPIView):
    def delete(self, request, slug, project_id, opp_id, pk):
        member = ConsortiumMember.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not member:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Meeting CRUD
# ---------------------------------------------------------------------------


class MeetingListCreateView(BaseAPIView):
    def get(self, request, slug, project_id, opp_id):
        meetings = Meeting.objects.filter(
            opportunity_id=opp_id,
            opportunity__issue__project_id=project_id,
            opportunity__issue__workspace__slug=slug,
        )
        return Response(MeetingSerializer(meetings, many=True).data)

    def post(self, request, slug, project_id, opp_id):
        opportunity = FundingOpportunity.objects.filter(
            pk=opp_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug,
        ).first()
        if not opportunity:
            return Response(
                {"error": "Opportunity not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(opportunity=opportunity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MeetingDetailView(BaseAPIView):
    def get(self, request, slug, project_id, opp_id, pk):
        meeting = Meeting.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not meeting:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(MeetingSerializer(meeting).data)

    def patch(self, request, slug, project_id, opp_id, pk):
        meeting = Meeting.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not meeting:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = MeetingSerializer(
            meeting, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug, project_id, opp_id, pk):
        meeting = Meeting.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not meeting:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        meeting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Implementation Milestone CRUD
# ---------------------------------------------------------------------------


class MilestoneListCreateView(BaseAPIView):
    def get(self, request, slug, project_id, opp_id):
        milestones = ImplementationMilestone.objects.filter(
            opportunity_id=opp_id,
            opportunity__issue__project_id=project_id,
            opportunity__issue__workspace__slug=slug,
        )
        return Response(
            ImplementationMilestoneSerializer(milestones, many=True).data
        )

    def post(self, request, slug, project_id, opp_id):
        opportunity = FundingOpportunity.objects.filter(
            pk=opp_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug,
        ).first()
        if not opportunity:
            return Response(
                {"error": "Opportunity not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ImplementationMilestoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(opportunity=opportunity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MilestoneDetailView(BaseAPIView):
    def patch(self, request, slug, project_id, opp_id, pk):
        milestone = ImplementationMilestone.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not milestone:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = ImplementationMilestoneSerializer(
            milestone, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug, project_id, opp_id, pk):
        milestone = ImplementationMilestone.objects.filter(
            pk=pk, opportunity_id=opp_id
        ).first()
        if not milestone:
            return Response(
                {"error": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )
        milestone.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
