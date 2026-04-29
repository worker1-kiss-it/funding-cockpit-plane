# Generated for the funding-cockpit chat rework (Phase 3).
#
# Adds FundingChatSession + FundingChatMessage so the new claude-CLI-backed
# chat has a persistent, searchable history independent of the CLI's on-disk
# session files. The CLI session files (under /root/.claude) hold the actual
# conversation context used by --resume; the rows below are the user-facing log.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from plane.db.models.base import BaseModel  # noqa: F401  (kept for parity)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("db", "0121_alter_estimate_type"),
        ("funding", "0002_fundingopportunity_linked_docs_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FundingChatSession",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ("claude_session_id", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("title", models.CharField(blank=True, default="", max_length=200)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="funding_fundingchatsession_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="funding_fundingchatsession_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="funding_chat_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="funding_chat_sessions",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Funding Chat Session",
                "verbose_name_plural": "Funding Chat Sessions",
                "db_table": "funding_chat_sessions",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="FundingChatMessage",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("assistant", "Assistant"),
                            ("system", "System"),
                            ("tool", "Tool"),
                        ],
                        max_length=16,
                    ),
                ),
                ("content", models.TextField()),
                ("tokens_in", models.IntegerField(blank=True, null=True)),
                ("tokens_out", models.IntegerField(blank=True, null=True)),
                ("cost_usd", models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                ("raw", models.JSONField(blank=True, help_text="Raw stream-json events from the claude CLI for debugging", null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="funding_fundingchatmessage_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="funding_fundingchatmessage_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="funding.fundingchatsession",
                    ),
                ),
            ],
            options={
                "verbose_name": "Funding Chat Message",
                "verbose_name_plural": "Funding Chat Messages",
                "db_table": "funding_chat_messages",
                "ordering": ["created_at"],
            },
        ),
    ]
