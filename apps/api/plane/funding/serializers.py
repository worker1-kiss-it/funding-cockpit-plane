from rest_framework import serializers

from .models import FundingOpportunity, FundingActivityLog


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


class FundingOpportunitySerializer(serializers.ModelSerializer):
    activity_logs = FundingActivityLogSerializer(many=True, read_only=True)
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
            "activity_logs",
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
        ]


class FundingDashboardSerializer(serializers.Serializer):
    total_opportunities = serializers.IntegerField()
    by_phase = serializers.DictField()
    by_type = serializers.DictField()
    high_priority = serializers.IntegerField()
    deadlines_this_month = serializers.IntegerField()
    urgent_deadlines = serializers.IntegerField()
