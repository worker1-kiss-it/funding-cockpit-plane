from rest_framework import serializers

from .models import (
    FundingOpportunity,
    FundingActivityLog,
    Proposal,
    Partner,
    ConsortiumMember,
    Meeting,
    ImplementationMilestone,
)


class FundingActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingActivityLog
        fields = [
            "id",
            "user_email",
            "field",
            "old_value",
            "new_value",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = [
            "id",
            "opportunity",
            "title",
            "version",
            "status",
            "submission_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PartnerSerializer(serializers.ModelSerializer):
    consortium_count = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "workspace",
            "name",
            "organization_type",
            "country",
            "contact_name",
            "contact_email",
            "expertise",
            "website",
            "notes",
            "consortium_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace", "created_at", "updated_at"]

    def get_consortium_count(self, obj):
        return obj.consortium_memberships.count()


class ConsortiumMemberSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source="partner.name", read_only=True)
    partner_country = serializers.CharField(
        source="partner.country", read_only=True
    )
    partner_type = serializers.CharField(
        source="partner.organization_type", read_only=True
    )

    class Meta:
        model = ConsortiumMember
        fields = [
            "id",
            "opportunity",
            "partner",
            "partner_name",
            "partner_country",
            "partner_type",
            "role",
            "work_package",
            "budget_share",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = [
            "id",
            "opportunity",
            "title",
            "date",
            "attendees",
            "notes",
            "action_items",
            "meeting_type",
            "location",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ImplementationMilestoneSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = ImplementationMilestone
        fields = [
            "id",
            "opportunity",
            "title",
            "due_date",
            "completed_date",
            "status",
            "deliverable",
            "notes",
            "budget_spent",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_overdue(self, obj):
        from datetime import date

        if obj.due_date and obj.status not in ("completed",):
            return obj.due_date < date.today()
        return False


class FundingOpportunitySerializer(serializers.ModelSerializer):
    activity_logs = FundingActivityLogSerializer(many=True, read_only=True)
    proposals = ProposalSerializer(many=True, read_only=True)
    consortium_members = ConsortiumMemberSerializer(
        many=True, read_only=True
    )
    meetings = MeetingSerializer(many=True, read_only=True)
    milestones = ImplementationMilestoneSerializer(
        many=True, read_only=True
    )
    issue_name = serializers.CharField(source="issue.name", read_only=True)
    issue_state = serializers.CharField(
        source="issue.state.name", read_only=True
    )
    issue_state_group = serializers.CharField(
        source="issue.state.group", read_only=True
    )
    issue_priority = serializers.CharField(
        source="issue.priority", read_only=True
    )
    issue_assignees = serializers.SerializerMethodField()
    issue_target_date = serializers.DateField(
        source="issue.target_date", read_only=True
    )

    class Meta:
        model = FundingOpportunity
        fields = [
            "id",
            "issue",
            "external_id",
            "opportunity_type",
            "budget",
            "relevance",
            "fit_notes",
            "source",
            "url",
            "call_id",
            "next_step",
            "deadline",
            "linked_docs",
            "tags",
            "activity_logs",
            "proposals",
            "consortium_members",
            "meetings",
            "milestones",
            "issue_name",
            "issue_state",
            "issue_state_group",
            "issue_priority",
            "issue_assignees",
            "issue_target_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_issue_assignees(self, obj):
        return list(
            obj.issue.assignees.values_list("display_name", flat=True)
        )


class FundingOpportunityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingOpportunity
        fields = [
            "relevance",
            "fit_notes",
            "next_step",
            "budget",
            "url",
            "source",
            "linked_docs",
            "tags",
        ]


class FundingDashboardSerializer(serializers.Serializer):
    total_opportunities = serializers.IntegerField()
    by_phase = serializers.DictField()
    by_type = serializers.DictField()
    high_priority = serializers.IntegerField()
    deadlines_this_month = serializers.IntegerField()
    urgent_deadlines = serializers.IntegerField()
