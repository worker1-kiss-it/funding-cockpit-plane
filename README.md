# Funding Cockpit (Plane-Based)

Central management platform for EU funding opportunities, built on top of [Plane](https://plane.so/) (open-source project management). Extends Plane with funding-specific models, a knowledge base, AI chat, partner/consortium management, proposal tracking, and a two-project task workflow.

## Live URLs

| Environment             | URL                                                  |
| ----------------------- | ---------------------------------------------------- |
| **Production App**      | https://plane.46.225.111.79.nip.io/                  |
| **Admin Panel**         | https://plane.46.225.111.79.nip.io/god-mode/         |
| **Old Funding Cockpit** | https://funding.kiss-it.io/ (FastAPI, still running) |

## Login

Authentication is via **magic link** (email verification code) -- no passwords. Configured users:

- `g.kiss@kiss-it.io` (Gergo Kiss) -- instance admin
- `r.hasan@kiss-it.io` (Raquibul Hasan)
- `shafi@mediprospects.ai` (Shafi Choudhury)

SMTP is configured via `smtp.easyname.eu` (sender: `worker1.kiss@kiss-it.io`).

## Quick Start (What You See After Login)

The app auto-redirects to the **EU Funding Pipeline board view** -- a kanban board with 12 pipeline columns showing all 160 opportunities. The sidebar shows:

1. **Favorites** (expanded at top) -- quick links to key views:
   - EU Funding Pipeline (board view)
   - Deadline Calendar
   - Active Opportunities
   - High Priority
   - Upcoming Deadlines
   - Won Projects
   - Spreadsheet Overview
2. **Workspace** -- Funding Dashboard, Knowledge Base, Projects
3. **Projects** (collapsed) -- EU Funding Pipeline, Funding Tasks

## Two-Project Workflow

| Project                 | Identifier | Purpose                                                    |
| ----------------------- | ---------- | ---------------------------------------------------------- |
| **EU Funding Pipeline** | FUND       | Opportunities only -- clean kanban pipeline board          |
| **Funding Tasks**       | TASK       | Action items, deliverables, to-dos linked to opportunities |

**Why two projects?** Sub-work items in Plane appear as standalone cards on the board, cluttering the pipeline view. Keeping opportunities and tasks in separate projects keeps the pipeline clean while allowing full task management.

**How to create a task for an opportunity:**

1. Open any opportunity (e.g. FUND-146 GenAI-Cybersecure EU)
2. Click **"Create task"** button (in the action bar next to "Add sub-work item", "Add relation", etc.)
3. Enter a task name -- the task is created in the TASK project with an automatic `relates_to` relation back to the opportunity
4. The relation is visible on both sides (opportunity shows linked tasks, task shows linked opportunity)

## Architecture

```
Internet
  │
  ▼
nginx (host, ports 80/443, Let's Encrypt + HSTS)
  │
  ▼
Caddy reverse proxy (internal, 127.0.0.1:8800, security headers)
  ├─► web         (React frontend, port 3000)
  ├─► admin       (Admin dashboard, port 3000)
  ├─► space       (Public space, port 3000)
  ├─► api         (Django REST API, port 8000)
  ├─► live        (WebSocket collaboration, port 3000)
  └─► plane-minio (S3-compatible file storage, port 9000)

api ─► plane-db          (PostgreSQL 15.7)
api ─► plane-redis       (Valkey/Redis 7.2.11)
api ─► plane-mq          (RabbitMQ 3.13.6)
api ─► /app/kb           (Legacy KB read-only bind mount from /git/funding-cockpit/kb)
api ─► /app/pages-cache  (Bind mount of /srv/funding-cockpit/pages-cache; Plane Pages
                          dumped here every 10 min by a celery beat task)

api ─HTTP+bearer──► host.docker.internal:5557
                    │
                    │  (extra_hosts: host-gateway, ufw allow 172.17/16+172.28/16)
                    ▼
              ┌──────────────────────────────────────────────┐
              │  claude-exec-server (host, systemd --user)   │
              │  - Flask + waitress, listens on 0.0.0.0:5557 │
              │  - bearer-auth, argv list, prompt via stdin  │
              │  - --allowedTools "Read"                     │
              │  - --add-dir /git/funding-cockpit/kb         │
              │  - --add-dir /srv/funding-cockpit/pages-cache│
              │  - --session-id / --resume                   │
              └────────────────────────┬─────────────────────┘
                                       ▼
                              claude --print --output-format stream-json
                              (runs as `clauderunner`, OAuth via
                               ~/.claude/, NO ANTHROPIC_API_KEY)
```

**Why a host-side server?** The Anthropic CLI is OAuth-authenticated against
the user account that ran `claude login` — that auth lives in
`~clauderunner/.claude/`. Rather than bundling Node.js + the CLI + an API
key into the api image, the api container POSTs each chat turn over the
docker bridge to a small Python server running on the host as `clauderunner`,
which shells out to the locally-installed CLI. The api image stays lean,
no API key ever lives on disk, and re-auth is just `claude` in a terminal
followed by `systemctl --user restart claude-exec.service`.

## Tech Stack

| Component     | Technology                                                |
| ------------- | --------------------------------------------------------- |
| Backend       | Python/Django 4.2 + Django REST Framework                 |
| Frontend      | React + TypeScript (Vite/React Router)                    |
| Database      | PostgreSQL 15.7                                           |
| Cache         | Redis (Valkey 7.2.11)                                     |
| Message Queue | RabbitMQ 3.13.6                                           |
| File Storage  | MinIO (S3-compatible)                                     |
| Reverse Proxy | Caddy (internal) + nginx (external, SSL, HSTS)            |
| AI Chat       | Local `claude` CLI (Anthropic Claude Code), SSE streaming |
| Auth          | Magic link (email code, JWT sessions)                     |

## Comparison: Old vs New

| Feature                       | Old (FastAPI + Alpine.js) | New (Plane-Based)                                                                        |
| ----------------------------- | ------------------------- | ---------------------------------------------------------------------------------------- |
| **Pipeline/Kanban**           | Custom 12-phase board     | Plane native board + 12 custom states                                                    |
| **Calendar**                  | Custom calendar view      | Plane built-in calendar layout                                                           |
| **Task Management**           | None                      | Separate TASK project with linked tasks                                                  |
| **Gantt/Timeline**            | None                      | Plane built-in timeline view                                                             |
| **Spreadsheet View**          | None                      | Plane built-in spreadsheet layout                                                        |
| **Knowledge Base**            | Custom file tree browser  | Custom KB browser page in Plane sidebar                                                  |
| **AI Chat**                   | WebSocket sidebar         | Dark-themed slide-out drawer, server-side claude CLI, SSE streaming, persistent sessions |
| **Funding Dashboard**         | Custom stats page         | Custom dashboard page in Plane sidebar                                                   |
| **Activity Logging**          | JSON field                | Plane native + FundingActivityLog model                                                  |
| **Proposal Tracking**         | None                      | Proposal model on issue detail sidebar                                                   |
| **Partner Management**        | None                      | Partner + ConsortiumMember on issue detail                                               |
| **Meeting Tracking**          | None                      | Meeting model on issue detail sidebar                                                    |
| **Implementation Milestones** | None                      | ImplementationMilestone on issue detail                                                  |
| **Multi-Tenant**              | Single tenant             | Workspace isolation (one per company)                                                    |
| **Real-time Collaboration**   | None                      | Plane live server (WebSocket)                                                            |
| **File Attachments**          | Linked doc paths          | MinIO storage + linked docs preserved                                                    |
| **Search**                    | Full-text .md/.txt        | Full-text KB search + Plane native search                                                |
| **User Management**           | Allowed emails list       | Full RBAC (admin, member, guest)                                                         |
| **Saved Views / Quick Links** | None                      | Favorited views in sidebar (board, calendar, etc.)                                       |
| **Dark Mode**                 | Custom dark theme         | Plane native dark mode (default)                                                         |
| **Database**                  | JSON file                 | PostgreSQL                                                                               |

## Frontend Extensions (Plane UI)

All custom frontend code uses Plane's CE (Community Edition) extension system, keeping customizations cleanly separated from core code.

### Sidebar Navigation

- **Funding Dashboard** -- stats cards, phase distribution, upcoming deadlines table
- **Knowledge Base** -- legacy file tree browser, kept as a fallback for one
  release while users migrate to the new **Knowledge Base project** (`KB`),
  which holds the same content as Plane Pages with versioning, live
  collaboration, and full-text search

Both are pinned in the sidebar under "Workspace" for all users.

### Favorites (Quick Links)

Pre-configured saved views favorited for all users, shown expanded at top of sidebar:

- EU Funding Pipeline (project -- opens board view)
- Deadline Calendar, Active Opportunities, High Priority, Upcoming Deadlines, Won Projects, Spreadsheet Overview

### Issue Detail Sidebar -- Funding Properties

When viewing any opportunity, the right sidebar shows additional funding fields:

- Relevance (1-5 interactive star rating)
- Budget, External ID, Opportunity Type, Source URL, Deadline
- Fit Notes, Next Step
- Collapsible sections: Linked Docs, Proposals, Consortium, Meetings, Milestones, Tasks

### Issue Detail Action Bar -- "Create Task" Button

A **"Create task"** button appears next to "Add sub-work item", "Add relation", "Add link", "Attach". Clicking it:

1. Prompts for a task name
2. Creates the task in the Funding Tasks (TASK) project
3. Auto-creates a `relates_to` relation linking it to the opportunity
4. Keeps the FUND pipeline board clean

### AI Chat Drawer

Floating chat button (bottom-right) on all pages. Opens a dark-themed slide-out drawer:

- Streams replies from the local `claude` CLI via SSE; renders markdown
- Multi-session: history button lists prior conversations, plus button starts a new one
- Per-message token + cost footer
- Solid dark background matching Plane's dark mode theme

### Default User Experience

- Dark mode enabled by default
- Board layout (kanban) as default view for issues
- Favorites expanded at top of sidebar
- Projects section collapsed
- Workspace home auto-redirects to the pipeline board view

## New User Auto-Provisioning

A Django signal (`post_save` on `WorkspaceMember`) automatically provisions defaults for any new user added to a workspace with a FUND project:

- Profile created with onboarding skipped
- Dark mode enabled
- Board layout set as default
- All saved views favorited
- Funding Dashboard + Knowledge Base pinned in sidebar
- Added as member to the FUND project (and to the KB project if it exists)

## Data Migrated

| Data                         | Count                                              | Notes                                                                                                                                                                           |
| ---------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Opportunities                | 160 (151 imported + 9 seed)                        | All phases, priorities, assignees preserved                                                                                                                                     |
| Activity Logs                | 118                                                | Historical change tracking                                                                                                                                                      |
| Linked Documents             | 148 opportunities with 341 refs                    | Stored as JSON paths, resolved via KB endpoint                                                                                                                                  |
| KB Files (legacy filesystem) | 418 files (125 MB)                                 | Mounted read-only from old cockpit                                                                                                                                              |
| **KB → Plane Pages**         | **513 pages** + **131 binary FileAssets** in MinIO | Folders → page hierarchy; PDFs/DOCX text-extracted via `pypdf`/`python-docx` and inlined; binaries linked from a stub page; idempotent re-runs via `Page.external_id = "kb-fs"` |
| Projects (\_index.md)        | 18 across 3 categories                             | Full Match, ESR Only, Proposal Only                                                                                                                                             |
| Labels                       | 13 normalized from 34 type variants                | Horizon Europe, Cascade, Digital Europe, etc.                                                                                                                                   |
| Pipeline States              | 12                                                 | Backlog -> Discovery -> ... -> Won/Rejected/Archived                                                                                                                            |

## Custom Funding Extension (Backend)

Located in `apps/api/plane/funding/`. Registered in `INSTALLED_APPS` as `plane.funding`.

### Models (`models.py`)

- **FundingOpportunity** -- 1:1 linked to Plane Issue. Fields: external_id, opportunity_type, budget, relevance (1-5), fit_notes, source, url, call_id, next_step, deadline, linked_docs (JSON), tags (JSON)
- **FundingActivityLog** -- Change tracking per opportunity
- **Proposal** -- Draft/review/submission tracking per opportunity
- **Partner** -- Workspace-scoped partner directory (org type, country, contact, expertise)
- **ConsortiumMember** -- Links partner to opportunity with role (coordinator, partner, subcontractor)
- **Meeting** -- Meeting/call tracking per opportunity (internal, partner, info day, review, kickoff)
- **ImplementationMilestone** -- Post-award deliverable tracking with status and due dates
- **FundingChatSession** -- One persistent chat session per (workspace, user). Holds the `claude_session_id` UUID passed to `claude --session-id` / `--resume` so multi-turn context survives restarts.
- **FundingChatMessage** -- One message in a session (`user`/`assistant`/`system`/`tool`). Stores `tokens_in`, `tokens_out`, `cost_usd`, plus the raw stream-json events for debugging.

### API Endpoints

All under `/api/funding/`:

**Pipeline & Dashboard:**

```
GET  /workspaces/{slug}/projects/{id}/funding/pipeline/
GET  /workspaces/{slug}/projects/{id}/funding/dashboard/
GET  /workspaces/{slug}/projects/{id}/funding/deadlines/
GET|PATCH /workspaces/{slug}/projects/{id}/funding/{opp_id}/
```

**Proposals:**

```
GET|POST /workspaces/{slug}/projects/{id}/funding/{opp_id}/proposals/
GET|PATCH|DELETE /workspaces/{slug}/projects/{id}/funding/{opp_id}/proposals/{pk}/
```

**Partners (workspace-scoped):**

```
GET|POST /workspaces/{slug}/funding/partners/
GET|PATCH|DELETE /workspaces/{slug}/funding/partners/{pk}/
```

**Consortium:**

```
GET|POST /workspaces/{slug}/projects/{id}/funding/{opp_id}/consortium/
DELETE /workspaces/{slug}/projects/{id}/funding/{opp_id}/consortium/{pk}/
```

**Meetings:**

```
GET|POST /workspaces/{slug}/projects/{id}/funding/{opp_id}/meetings/
GET|PATCH|DELETE /workspaces/{slug}/projects/{id}/funding/{opp_id}/meetings/{pk}/
```

**Milestones:**

```
GET|POST /workspaces/{slug}/projects/{id}/funding/{opp_id}/milestones/
PATCH|DELETE /workspaces/{slug}/projects/{id}/funding/{opp_id}/milestones/{pk}/
```

**Knowledge Base:**

```
GET /workspaces/{slug}/projects/{id}/funding/kb/tree/
GET /workspaces/{slug}/projects/{id}/funding/kb/file/?path=...
GET /workspaces/{slug}/projects/{id}/funding/kb/file/raw/?path=...
GET /workspaces/{slug}/projects/{id}/funding/kb/search/?q=...
GET /workspaces/{slug}/projects/{id}/funding/kb/projects/
```

**AI Chat (host claude-exec backend, SSE streaming):**

```
GET    /workspaces/{slug}/projects/{id}/funding/chat/sessions/
POST   /workspaces/{slug}/projects/{id}/funding/chat/sessions/
GET    /workspaces/{slug}/projects/{id}/funding/chat/sessions/{session_id}/messages/
POST   /workspaces/{slug}/projects/{id}/funding/chat/sessions/{session_id}/messages/   # text/event-stream
```

`POST .../messages/` returns Server-Sent Events: `open` → one or more
`delta` chunks → a final `done` event carrying `tokens_in`, `tokens_out`,
`cost_usd`, and the persisted `message_id` (or an `error` event if the
host server / CLI failed). User-facing history is stored in Postgres
(`funding_chat_messages`); the actual CLI conversation state lives in
`~clauderunner/.claude/projects/<hash>/<session-id>/` on the host so
multi-turn context survives api restarts.

Throttle scopes (DRF `ScopedRateThrottle`):

- `funding_chat` -- 30/min/user
- `funding_kb_search` -- 60/min/user
- `funding_kb_raw` -- 120/min/user

**Linked Tasks:**

```
POST /workspaces/{slug}/projects/{id}/funding/create-task/{issue_id}/
```

## Management Commands

```bash
# Seed initial data (users, workspace, project, states, labels, 9 sample opportunities)
python manage.py seed_funding_data

# Import all opportunities from production JSON
python manage.py import_opportunities --file /app/kb/opportunities.json --workspace funding-cockpit --project FUND

# Dry run (shows what would be imported)
python manage.py import_opportunities --dry-run

# Create a new tenant/company workspace
python manage.py create_tenant --name "Company Name" --slug company-slug --admin admin@email.com

# Migrate the on-disk KB into Plane native Pages (creates a `KB` project per
# workspace, walks /app/kb, materialises folders as page hierarchy, uploads
# binaries to MinIO, inlines extracted PDF/DOCX text). Idempotent — re-runs
# update existing pages in place.
python manage.py import_kb_to_pages --dry-run
python manage.py import_kb_to_pages
python manage.py import_kb_to_pages --workspace funding-cockpit
```

### Background tasks

`apps/api/plane/funding/tasks.py` registers `dump_pages_for_chat` on the
celery beat schedule (every 10 minutes). It walks every Plane Page and
dumps a markdown snapshot to `/app/pages-cache/<workspace>/<project>/<slug>.md`.
That directory is bind-mounted to `/srv/funding-cockpit/pages-cache` on the
host, which the claude-exec server exposes to the CLI via `--add-dir`.

To force a refresh:

```bash
docker compose -p funding-plane exec api python manage.py shell -c \
  "from plane.funding.tasks import dump_pages_for_chat; print(dump_pages_for_chat(force=True))"
```

## Multi-Tenant

Each company gets its own **Plane workspace** with full data isolation. Users can belong to multiple workspaces and switch between them via the workspace dropdown at the top-left.

To add a second company:

```bash
docker compose -p funding-plane exec api python manage.py create_tenant \
  --name "Other Company" --slug other-company --admin user@other.com
```

This creates a workspace with the standard 12-phase pipeline, type labels, and a "EU Funding Pipeline" project. New users added to the workspace automatically get all defaults (dark mode, board layout, favorites) via the Django signal.

To add a user to multiple workspaces:

```bash
docker compose -p funding-plane exec api python manage.py shell -c "
from plane.db.models import User, Workspace, WorkspaceMember
user = User.objects.get(email='user@example.com')
ws = Workspace.objects.get(slug='other-company')
WorkspaceMember.objects.get_or_create(workspace=ws, member=user, defaults={'role': 20})
"
```

Roles are per-workspace: Admin (20), Member (15), Guest (5).

## Deployment

```bash
# Build and start all services
docker compose -p funding-plane up -d --build

# Check status
docker compose -p funding-plane ps

# View logs
docker compose -p funding-plane logs -f api

# Run migrations after model changes
docker compose -p funding-plane exec api python manage.py makemigrations funding
docker compose -p funding-plane exec api python manage.py migrate funding

# Import data
docker compose -p funding-plane exec api python manage.py import_opportunities
```

For day-2 operations (rollback, secret rotation, restoring from backup,
chat troubleshooting, MinIO ops) see [`docs/RUNBOOK.md`](docs/RUNBOOK.md).
For the threat model, data classification, and AI sandbox controls see
[`docs/SECURITY.md`](docs/SECURITY.md).

### Environment Files

- `.env` -- Root env (PostgreSQL, Redis, RabbitMQ, MinIO credentials, ports, `LIVE_SERVER_SECRET_KEY`)
- `apps/api/.env` -- API env (database URL, SMTP, `CLAUDE_EXEC_URL`/`CLAUDE_EXEC_TOKEN`, base URLs, auth config). **Gitignored.**
- `apps/web/.env` -- Frontend env (API base URL)
- `apps/admin/.env`, `apps/space/.env`, `apps/live/.env` -- Service-specific env

`*.env.example` files in the repo are placeholders only. Real values are
generated on the host and never committed. CI runs `gitleaks` on every PR
to enforce this.

### Key Environment Variables

| Variable                  | Purpose                                                                | Default                            |
| ------------------------- | ---------------------------------------------------------------------- | ---------------------------------- |
| `KB_PATH`                 | Legacy knowledge base directory mount inside the api container         | `/app/kb`                          |
| `PAGES_CACHE_PATH`        | Where the Plane Pages dump task writes for the chat assistant          | `/app/pages-cache`                 |
| `CLAUDE_EXEC_URL`         | URL of the host claude-exec server                                     | `http://host.docker.internal:5557` |
| `CLAUDE_EXEC_TOKEN`       | Bearer token shared with the host server (rotate together)             | (required)                         |
| `CLAUDE_TIMEOUT_SECONDS`  | Per-call wall-clock timeout the api enforces on top of the host server | `180`                              |
| `SENTRY_DSN`              | Sentry DSN for error monitoring (optional)                             | (unset = disabled)                 |
| `SENTRY_ENVIRONMENT`      | Tag for Sentry events                                                  | `production`                       |
| `LIVE_SERVER_SECRET_KEY`  | Shared secret between the api and the live (collab) service            | (required, env-var'd in compose)   |
| `EMAIL_HOST`              | SMTP server for magic link                                             | `smtp.easyname.eu`                 |
| `EMAIL_HOST_USER`         | SMTP username                                                          | `worker1.kiss@kiss-it.io`          |
| `SKIP_ENV_VAR`            | Read config from env vars (0) or DB (1)                                | `0`                                |
| `ENABLE_SIGNUP`           | Allow new user registration                                            | `1`                                |
| `ENABLE_MAGIC_LINK_LOGIN` | Enable email code login                                                | `1`                                |

The host claude-exec server reads its own env vars from
`~/.config/systemd/user/claude-exec.service`:

| Variable                 | Purpose                                              | Default                                                    |
| ------------------------ | ---------------------------------------------------- | ---------------------------------------------------------- |
| `CLAUDE_EXEC_HOST`       | Bind address                                         | `0.0.0.0` (firewalled by ufw)                              |
| `CLAUDE_EXEC_PORT`       | Bind port                                            | `5557`                                                     |
| `CLAUDE_EXEC_TOKEN_FILE` | File holding the bearer token (mode 0600)            | `/home/clauderunner/claude-exec-server/token`              |
| `CLAUDE_TIMEOUT_SECONDS` | Per-request wall-clock timeout (kills process group) | `180`                                                      |
| `CLAUDE_MAX_CONCURRENCY` | Concurrency cap on simultaneous CLI subprocesses     | `4`                                                        |
| `CLAUDE_MODEL`           | Default model for the CLI (alias or full id)         | `claude-sonnet-4-6`                                        |
| `CLAUDE_ALLOWED_DIRS`    | Comma-separated list of dirs added via `--add-dir`   | `/git/funding-cockpit/kb,/srv/funding-cockpit/pages-cache` |

## Host claude-exec Server

The chat backend lives **outside** the api container so it can use the
locally-installed, OAuth-authenticated `claude` CLI without an
`ANTHROPIC_API_KEY`. Source, systemd unit, and install instructions are in
[`deployments/claude-exec/`](deployments/claude-exec/).

| Aspect                         | Detail                                                                                                                                                                                                                                   |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Source**                     | `/home/clauderunner/claude-exec-server/server.py` (mirrored at `deployments/claude-exec/server.py`)                                                                                                                                      |
| **Runtime**                    | Flask + waitress in a venv at `/home/clauderunner/claude-exec-server/venv/`                                                                                                                                                              |
| **Auth**                       | Bearer token in `/home/clauderunner/claude-exec-server/token` (mode 0600). The same value lives in `apps/api/.env` as `CLAUDE_EXEC_TOKEN`.                                                                                               |
| **Process supervision**        | `systemctl --user` unit at `~/.config/systemd/user/claude-exec.service`, with `loginctl enable-linger clauderunner` so it survives reboots                                                                                               |
| **Bind address**               | `0.0.0.0:5557`, firewalled by ufw to `172.17.0.0/16` and `172.28.0.0/16` (the docker bridges)                                                                                                                                            |
| **CLI flags it always passes** | `--print --output-format stream-json --include-partial-messages --verbose --model claude-sonnet-4-6 --allowedTools "Read" --add-dir <each CLAUDE_ALLOWED_DIR>` plus `--session-id <uuid>` (first turn) or `--resume <uuid>` (follow-ups) |
| **What request bodies can do** | Set `prompt`, `session_id`, `resume`, and (optionally) `model`/`system_prompt`. Nothing else. The argv is fixed in `_build_argv`; the prompt is passed on **stdin**, never argv, so it can't be seen in `ps` or hit argv length limits.  |
| **What it can't do**           | No `Bash`, `Edit`, `Write`, `WebFetch`, etc. — only `Read`. No filesystem access outside `--add-dir` whitelist. No shell parsing of any user-controlled string (`subprocess.Popen` with argv list, never `shell=True`).                  |
| **Concurrency cap**            | `threading.BoundedSemaphore(CLAUDE_MAX_CONCURRENCY)`; over-limit requests block up to 30 s and then return `{"type":"error","message":"server busy"}`                                                                                    |
| **Watchdog**                   | `threading.Timer(CLAUDE_TIMEOUT_SECONDS, …)` that `os.killpg(SIGKILL)` on timeout                                                                                                                                                        |
| **Logs**                       | Structured JSON to `/home/clauderunner/claude-exec-server/server.log` (rid, session_id, duration_ms, exit code)                                                                                                                          |

### Day-2 operations

```bash
# status / restart
sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/1001 \
    systemctl --user status claude-exec.service
sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/1001 \
    systemctl --user restart claude-exec.service

# follow logs
tail -f /home/clauderunner/claude-exec-server/server.log

# health probe (from anywhere on the host)
curl -s http://127.0.0.1:5557/health

# rotate the bearer token
sudo -u clauderunner python3 -c 'import secrets; print(secrets.token_urlsafe(48))' \
    | sudo -u clauderunner tee /home/clauderunner/claude-exec-server/token >/dev/null
sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/1001 \
    systemctl --user restart claude-exec.service
# then update CLAUDE_EXEC_TOKEN in apps/api/.env and:
sudo docker compose -p funding-plane restart api worker beat-worker

# re-authenticate the underlying claude CLI (when OAuth expires)
sudo -u clauderunner /home/clauderunner/.local/bin/claude   # finish the login flow, exit
sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/1001 \
    systemctl --user restart claude-exec.service
```

## Production hardening

The repo went through a hardening pass; the highlights are documented in
[`docs/SECURITY.md`](docs/SECURITY.md). Quick summary:

| Area                    | Control                                                                                                                                                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **TLS / headers**       | nginx terminates TLS (Let's Encrypt). HSTS (`max-age=31536000; includeSubDomains`), X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy added at the Caddy edge. Server header suppressed.                  |
| **Secrets**             | `apps/api/.env` and root `.env` are gitignored; no secrets ever land in git. `gitleaks` runs in CI and as a pre-commit hook. `LIVE_SERVER_SECRET_KEY` env-var'd in `docker-compose.yml` (no longer hardcoded). All defaults rotated. |
| **AI key surface**      | Zero. The api container has no `ANTHROPIC_API_KEY`. Auth lives in `~clauderunner/.claude/` and is gated by the bearer-token bridge.                                                                                                  |
| **Image pinning**       | All container images pinned to a tag (postgres 15.7-alpine, valkey 7.2.11-alpine, rabbitmq 3.13.6-management-alpine, minio `RELEASE.2025-02-07T23-21-09Z`).                                                                          |
| **AuthZ**               | DRF default is `IsAuthenticated`. `KBRawFileView` no longer overrides this (the previous bypass let any guesser exfiltrate KB files); regression-tested in `tests/test_kb_security.py`.                                              |
| **Rate limiting**       | `ScopedRateThrottle` on `funding_chat` (30/min/user), `funding_kb_search` (60/min/user), `funding_kb_raw` (120/min/user).                                                                                                            |
| **KB search hardening** | Time-bounded (≤2s wall clock), file-count-bounded (≤2000 scanned), result-bounded (≤20), HTML-escaped snippets, ≥3-char queries, path traversal + null-byte rejection in `_safe_path`.                                               |
| **Backups**             | `deployments/backups/backup.sh` does nightly `pg_dump                                                                                                                                                                                | gzip`+ tar of MinIO + tar of legacy KB, with`sha256sum`manifest. Restore is documented in`deployments/backups/RESTORE.md`. |
| **Monitoring**          | `sentry-sdk[django]` initialised in `production.py` when `SENTRY_DSN` is set (off by default).                                                                                                                                       |
| **CI**                  | `.github/workflows/ci.yml`: gitleaks scan, `ruff check plane/funding`, `pytest plane/funding`, `pnpm lint` + `pnpm typecheck`.                                                                                                       |
| **Pre-commit**          | `.pre-commit-config.yaml`: gitleaks, ruff, end-of-file/trailing-whitespace, detect-private-key, check-added-large-files.                                                                                                             |
| **Tests**               | `apps/api/plane/funding/tests/` — 18 currently passing, covering KB path-safety, auth-bypass regression, search bounds, chat input sanitisation, chat runner stream parsing.                                                         |

## Infrastructure

- **Server:** Hetzner CX43 VPS (46.225.111.79)
- **SSL:** Let's Encrypt via certbot, managed by nginx
- **nginx config:** `/etc/nginx/sites-enabled/plane.46.225.111.79.nip.io`
- **Docker project:** `funding-plane`
- **KB data:** Mounted from `/git/funding-cockpit/kb` (shared with old cockpit, read-only)
- **Page cache:** `/srv/funding-cockpit/pages-cache` (owned by `clauderunner`, bind-mounted into api/worker/beat at `/app/pages-cache`)
- **Claude exec server:** systemd `--user` unit running as `clauderunner` on `0.0.0.0:5557`, ufw-restricted to docker bridges
- **Old cockpit:** Still running at `funding-cockpit-app-1` on port 8101 (https://funding.kiss-it.io)

## Repository Structure

```
apps/
  api/                              # Django backend
    plane/
      funding/                      # Custom funding extension
        apps.py                     # AppConfig with signal registration
        models.py                   # FundingOpportunity, Proposal, Partner, etc.
        signals.py                  # Auto-provision defaults for new users
        views.py                    # Pipeline, Dashboard, CRUD, CreateLinkedTask
        views_kb.py                 # Legacy KB file serving (with auth + bounded search)
        views_projects.py           # Projects view (_index.md parser)
        serializers.py              # DRF serializers
        urls.py                     # All funding API routes
        chat/                       # AI Chat — HTTP client to host claude-exec server
          __init__.py
          runner.py                 #   sync HTTP+NDJSON client around CLAUDE_EXEC_URL
          views.py                  #   sessions + SSE message streaming + Postgres persistence
          system_prompt.py          #   funding-cockpit assistant briefing
        tasks.py                    # dump_pages_for_chat (celery beat task, every 10 min)
        management/commands/
          seed_funding_data.py      # Initial data seeding
          import_opportunities.py   # Opportunity import from JSON
          create_tenant.py          # Multi-tenant workspace setup
          import_kb_to_pages.py     # KB filesystem → Plane Pages migration (idempotent)
        migrations/
          0001_initial.py
          0002_fundingopportunity_linked_docs_and_more.py
          0003_chat_persistence.py  # FundingChatSession + FundingChatMessage
          0004_chat_soft_delete.py  # adds the SoftDeleteModel deleted_at column
        tests/                      # 18 tests: kb security, chat runner, chat input sanitisation
  web/                              # React frontend (Plane UI)
    core/
      services/
        funding.service.ts          # FundingService API client (chat now uses fetch+ReadableStream SSE)
    ce/
      store/
        funding/                    # MobX stores (dashboard, kb, chat, opportunity)
        root.store.ts               # Extended with FundingStore
      components/
        funding/
          dashboard/index.tsx       # Funding Dashboard page
          kb/index.tsx              # Knowledge Base browser (legacy, kept as fallback)
          chat/index.tsx            # AI Chat drawer (SSE streaming, sessions, react-markdown)
          properties/index.tsx      # Funding fields on issue detail sidebar
        issues/
          issue-details/
            additional-properties.tsx  # Wires FundingProperties into sidebar
          issue-detail-widgets/
            action-buttons.tsx      # "Create task" button in action bar
        workspace/sidebar/
          helper.tsx                # Sidebar icons for funding items
    app/
      (all)/[workspaceSlug]/(projects)/
        page.tsx                    # Auto-redirect to pipeline board
        sidebar.tsx                 # Favorites moved to top
        funding-dashboard/          # Dashboard route (layout + page)
        knowledge-base/             # KB route (layout + page)
      routes/
        extended.ts                 # Funding routes registration
  admin/                            # Admin dashboard
  space/                            # Public sharing
  live/                             # Real-time collaboration (WebSocket)
  proxy/                            # Caddy reverse proxy (HSTS + security headers)
packages/
  constants/src/workspace.ts        # Sidebar nav items
  i18n/src/locales/en/translations.ts  # Labels for sidebar items

deployments/
  backups/
    backup.sh                       # Nightly pg_dump + MinIO tar + KB tar with sha256 manifest
    RESTORE.md                      # Step-by-step restore procedure
  claude-exec/                      # Host claude-exec server deploy artefacts
    server.py                       #   Production-hardened Flask + waitress wrapper around `claude`
    claude-exec.service             #   systemd --user unit
    README.md                       #   One-time host install instructions

docs/
  RUNBOOK.md                        # Day-2 ops: deploy, rollback, secrets, chat troubleshooting, MinIO
  SECURITY.md                       # Threat model, data classification, AI sandbox controls

.github/workflows/ci.yml            # gitleaks + ruff + pytest funding + pnpm lint/typecheck
.pre-commit-config.yaml             # gitleaks + ruff + basic hygiene
```

## Based On

[Plane](https://github.com/makeplane/plane) -- AGPL-3.0 licensed open-source project management (~209K lines of code, ~144 contributors, est. 40-60K developer hours).
