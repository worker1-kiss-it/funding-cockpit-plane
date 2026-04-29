# Generated to add the SoftDeleteModel `deleted_at` column to the chat tables.
#
# 0003_chat_persistence created the tables but only included the
# TimeAuditModel + UserAuditModel fields, missing the `deleted_at` column
# that BaseModel inherits via SoftDeleteModel. Plane's SoftDeletionManager
# filters every queryset by ``deleted_at__isnull=True`` and every insert
# writes the column, so the tables are unusable without it. This migration
# adds the column on both new tables.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("funding", "0003_chat_persistence"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundingchatsession",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
        ),
        migrations.AddField(
            model_name="fundingchatmessage",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
        ),
    ]
