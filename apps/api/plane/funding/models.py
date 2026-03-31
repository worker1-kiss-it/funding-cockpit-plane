import uuid

from django.db import models
from django.conf import settings

from plane.db.models.base import BaseModel


class FundingOpportunity(BaseModel):
    """Extra funding metadata attached to a Plane Issue."""

    issue = models.OneToOneField(
        "db.Issue",
        on_delete=models.CASCADE,
        related_name="funding_meta",
    )
    external_id = models.CharField(
        max_length=64,
        help_text="Original ID from the funding cockpit, e.g. CASCADE-001",
    )
    opportunity_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Cascade, Horizon, MSCA, etc.",
    )
    budget = models.CharField(max_length=128, blank=True, default="")
    relevance = models.IntegerField(
        default=1,
        help_text="1-5 relevance score",
    )
    fit_notes = models.TextField(blank=True, default="")
    source = models.CharField(max_length=256, blank=True, default="")
    url = models.URLField(max_length=512, blank=True, default="")
    call_id = models.CharField(max_length=128, blank=True, default="")
    next_step = models.TextField(blank=True, default="")
    deadline = models.DateField(null=True, blank=True)
    linked_docs = models.JSONField(
        default=list,
        blank=True,
        help_text="List of KB file paths linked to this opportunity",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Opportunity tags",
    )

    class Meta:
        db_table = "funding_opportunities"
        verbose_name = "Funding Opportunity"
        verbose_name_plural = "Funding Opportunities"

    def __str__(self):
        return f"{self.external_id} - {self.issue.name}"


class FundingActivityLog(BaseModel):
    """Activity log entry for a funding opportunity."""

    opportunity = models.ForeignKey(
        FundingOpportunity,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    user_email = models.EmailField()
    field = models.CharField(max_length=64)
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")

    class Meta:
        db_table = "funding_activity_logs"
        ordering = ["-created_at"]
        verbose_name = "Funding Activity Log"
        verbose_name_plural = "Funding Activity Logs"

    def __str__(self):
        return f"{self.opportunity.external_id}: {self.field} changed"


class Proposal(BaseModel):
    """Tracks proposal documents and submission status for an opportunity."""

    opportunity = models.ForeignKey(
        FundingOpportunity,
        on_delete=models.CASCADE,
        related_name="proposals",
    )
    title = models.CharField(max_length=512)
    version = models.CharField(max_length=32, default="v1")
    status = models.CharField(
        max_length=32,
        choices=[
            ("draft", "Draft"),
            ("internal_review", "Internal Review"),
            ("submitted", "Submitted"),
            ("revision_requested", "Revision Requested"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="draft",
    )
    submission_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "funding_proposals"
        ordering = ["-created_at"]
        verbose_name = "Proposal"
        verbose_name_plural = "Proposals"

    def __str__(self):
        return f"{self.title} ({self.version})"


class Partner(BaseModel):
    """Organization in the consortium/partner network."""

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="funding_partners",
    )
    name = models.CharField(max_length=256)
    organization_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SME, University, Research Institute, Large Enterprise, NGO, Public Body",
    )
    country = models.CharField(max_length=64, blank=True, default="")
    contact_name = models.CharField(max_length=256, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    expertise = models.TextField(blank=True, default="")
    website = models.URLField(max_length=512, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "funding_partners"
        ordering = ["name"]
        verbose_name = "Partner"
        verbose_name_plural = "Partners"

    def __str__(self):
        return self.name


class ConsortiumMember(BaseModel):
    """Links a partner to a specific opportunity with a role."""

    opportunity = models.ForeignKey(
        FundingOpportunity,
        on_delete=models.CASCADE,
        related_name="consortium_members",
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="consortium_memberships",
    )
    role = models.CharField(
        max_length=64,
        choices=[
            ("coordinator", "Coordinator"),
            ("partner", "Partner"),
            ("subcontractor", "Subcontractor"),
            ("associated", "Associated Partner"),
        ],
        default="partner",
    )
    work_package = models.CharField(max_length=128, blank=True, default="")
    budget_share = models.CharField(max_length=64, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "funding_consortium_members"
        ordering = ["role", "partner__name"]
        verbose_name = "Consortium Member"
        verbose_name_plural = "Consortium Members"

    def __str__(self):
        return f"{self.partner.name} ({self.role}) in {self.opportunity.external_id}"


class Meeting(BaseModel):
    """Meeting/call tracking for an opportunity."""

    opportunity = models.ForeignKey(
        FundingOpportunity,
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    title = models.CharField(max_length=256)
    date = models.DateTimeField()
    attendees = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated names or emails",
    )
    notes = models.TextField(blank=True, default="")
    action_items = models.TextField(blank=True, default="")
    meeting_type = models.CharField(
        max_length=32,
        choices=[
            ("internal", "Internal"),
            ("partner", "Partner Call"),
            ("info_day", "Info Day"),
            ("review", "Review Meeting"),
            ("kickoff", "Kickoff"),
            ("progress", "Progress Meeting"),
        ],
        default="internal",
    )
    location = models.CharField(max_length=256, blank=True, default="")

    class Meta:
        db_table = "funding_meetings"
        ordering = ["-date"]
        verbose_name = "Meeting"
        verbose_name_plural = "Meetings"

    def __str__(self):
        return f"{self.title} ({self.date.strftime('%Y-%m-%d')})"


class ImplementationMilestone(BaseModel):
    """Track post-award implementation milestones for won opportunities."""

    opportunity = models.ForeignKey(
        FundingOpportunity,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    title = models.CharField(max_length=256)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("delayed", "Delayed"),
        ],
        default="pending",
    )
    deliverable = models.CharField(max_length=256, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    budget_spent = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "funding_milestones"
        ordering = ["due_date"]
        verbose_name = "Implementation Milestone"
        verbose_name_plural = "Implementation Milestones"

    def __str__(self):
        return f"{self.title} ({self.status})"
