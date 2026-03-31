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
