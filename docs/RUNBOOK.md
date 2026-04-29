# Funding Cockpit Runbook

Operational reference for the Plane-based Funding Cockpit at
`https://plane.46.225.111.79.nip.io/`. Read this before touching production.

## 1. Quick checks

```bash
# All containers should be Up
sudo docker compose -p funding-plane ps

# API health
curl -fsS https://plane.46.225.111.79.nip.io/api/instances/ | head

# Database connectivity
sudo docker compose -p funding-plane exec api python manage.py check
sudo docker compose -p funding-plane exec api python manage.py showmigrations funding

# Claude CLI present and authed
sudo docker compose -p funding-plane exec api claude --version
sudo docker compose -p funding-plane exec api sh -c 'echo $ANTHROPIC_API_KEY | head -c 8 ; echo'
```

## 2. Deploy

We deploy by SSH-ing to the Hetzner box, pulling, rebuilding, and rolling.

```bash
ssh root@46.225.111.79
cd /opt/funding-cockpit
git fetch && git status   # nothing untracked, no surprise local changes
git pull --ff-only

# Rebuild only what changed:
sudo docker compose -p funding-plane build api worker beat-worker web
# Apply migrations BEFORE swapping containers:
sudo docker compose -p funding-plane run --rm migrator
sudo docker compose -p funding-plane up -d
sudo docker compose -p funding-plane ps
sudo docker compose -p funding-plane logs --tail=200 api worker
```

If anything looks wrong, **roll back** by checking out the previous tag and
re-running `up -d` (image cache is fast).

## 3. Backups & restore

Backups run nightly via `deployments/backups/backup.sh` (cron'd at 03:15 UTC).
They land in `/var/backups/funding-cockpit/<UTC-timestamp>/`.

To restore see `deployments/backups/RESTORE.md`.

To take a manual snapshot before risky work:

```bash
sudo /opt/funding-cockpit/deployments/backups/backup.sh
```

## 4. Rotating the Anthropic API key

1. Generate the new key in https://console.anthropic.com/.
2. SSH to the box, edit `/opt/funding-cockpit/apps/api/.env`, replace
   `ANTHROPIC_API_KEY=...`.
3. `sudo docker compose -p funding-plane restart api worker beat-worker`.
4. `sudo docker compose -p funding-plane exec api claude --version` to confirm
   the binary is still healthy.
5. Open a chat in the UI and send a message. If it streams a reply, you're
   done. If not, check `docker logs api` for `ClaudeError` lines.
6. Revoke the old key in the Anthropic console.

## 5. Rotating other secrets

| Secret                          | Where                                        | After-change action                                                                                        |
| ------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY` (Django)           | `apps/api/.env`                              | restart `api worker beat-worker`; users must re-login                                                      |
| `LIVE_SERVER_SECRET_KEY`        | root `.env` AND `apps/api/.env` (must match) | restart `live api`                                                                                         |
| `POSTGRES_PASSWORD`             | root `.env` and `apps/api/.env`              | `ALTER USER plane WITH PASSWORD ...` inside the running DB, then restart `api worker beat-worker migrator` |
| `RABBITMQ_PASSWORD`             | root `.env` and `apps/api/.env`              | restart `plane-mq worker beat-worker`                                                                      |
| `AWS_SECRET_ACCESS_KEY` (MinIO) | root `.env` and `apps/api/.env`              | rotate via MinIO admin, restart `plane-minio api worker`                                                   |

## 6. Chat is slow / failing

1. `sudo docker compose -p funding-plane logs --tail=200 api | grep claude`
2. Look for `ClaudeError`, timeouts, or `exit code=` lines.
3. Check Anthropic status: https://status.anthropic.com/
4. Check concurrency: `CLAUDE_MAX_CONCURRENCY` defaults to 5; bump if you see
   the semaphore queueing.
5. Sessions live in the `claude_sessions` docker volume; if a session is
   wedged, the user can hit "New chat" in the drawer — this calls
   `POST /chat/sessions/` and starts a fresh `--session-id`.
6. Last resort: clear the volume:
   ```bash
   sudo docker compose -p funding-plane down api worker beat-worker
   sudo docker volume rm funding-plane_claude_sessions
   sudo docker compose -p funding-plane up -d
   ```
   This loses CLI-side context for in-flight chats but keeps every
   `FundingChatMessage` row in Postgres.

## 7. KB → Pages migration

The KB lives in two places during the cutover:

- Legacy filesystem at `/git/funding-cockpit/kb` → mounted read-only into
  the api container at `/app/kb`. Used by the old KB browser and by the
  chat runner via `--add-dir /app/kb`.
- Plane native Pages, populated by `import_kb_to_pages`.

To run / re-run the migration (idempotent):

```bash
sudo docker compose -p funding-plane exec api python manage.py import_kb_to_pages --dry-run
sudo docker compose -p funding-plane exec api python manage.py import_kb_to_pages
```

The chat assistant also reads `/app/pages-cache`, which is populated every
10 minutes by the celery beat task `plane.funding.dump_pages_for_chat`. To
force a refresh:

```bash
sudo docker compose -p funding-plane exec api \
  python manage.py shell -c \
  "from plane.funding.tasks import dump_pages_for_chat; print(dump_pages_for_chat(force=True))"
```

## 8. MinIO is full / out of space

```bash
sudo docker compose -p funding-plane exec plane-minio mc du local/uploads
sudo docker compose -p funding-plane exec api \
  python manage.py shell -c \
  "from plane.db.models import FileAsset; print(FileAsset.objects.filter(is_deleted=True).count())"
```

The daily `delete_unuploaded_file_asset` and `hard_delete` tasks clean up
soft-deleted assets after 60 days (`HARD_DELETE_AFTER_DAYS`). To force:

```bash
sudo docker compose -p funding-plane exec api \
  python -m celery -A plane call plane.bgtasks.deletion_task.hard_delete
```

## 9. Adding a new user

Magic-link login auto-provisions. To add a user as workspace member from the
shell (e.g. for a new tenant):

```bash
sudo docker compose -p funding-plane exec api python manage.py shell -c "
from plane.db.models import User, Workspace, WorkspaceMember
user, _ = User.objects.get_or_create(email='new@example.com')
ws = Workspace.objects.get(slug='funding-cockpit')
WorkspaceMember.objects.get_or_create(workspace=ws, member=user, defaults={'role': 15})
"
```

The `provision_funding_defaults` signal will then add them to FUND + KB
projects, set dark mode, favorite the saved views, etc.

## 10. Useful queries

```python
# Pipeline counts by state
from plane.db.models import Issue
from collections import Counter
Counter(Issue.objects.filter(project__identifier='FUND').values_list('state__name', flat=True))

# Chat usage in the last 7 days
from datetime import timedelta
from django.utils import timezone
from plane.funding.models import FundingChatMessage
since = timezone.now() - timedelta(days=7)
FundingChatMessage.objects.filter(created_at__gte=since, role='assistant').count()

# Sum of chat cost
sum(filter(None, FundingChatMessage.objects.filter(created_at__gte=since).values_list('cost_usd', flat=True)))
```
