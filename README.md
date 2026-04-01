# Funding Cockpit (Plane-Based)

Central management platform for EU funding opportunities, built on top of [Plane](https://plane.so/) (open-source project management). Extends Plane with funding-specific models, a knowledge base, AI chat, partner/consortium management, and proposal tracking.

## Live URLs

| Environment | URL |
|-------------|-----|
| **Production App** | https://plane.46.225.111.79.nip.io/ |
| **Admin Panel** | https://plane.46.225.111.79.nip.io/god-mode/ |
| **Old Funding Cockpit** | https://funding.kiss-it.io/ (FastAPI, still running) |

## Login

Authentication is via **magic link** (email verification code) -- no passwords. Configured users:

- `g.kiss@kiss-it.io` (Gergo Kiss) -- instance admin
- `r.hasan@kiss-it.io` (Raquibul Hasan)
- `shafi@mediprospects.ai` (Shafi Choudhury)

SMTP is configured via `smtp.easyname.eu` (sender: `worker1.kiss@kiss-it.io`).

## Architecture

```
nginx (ports 80/443, Let's Encrypt SSL)
  -> Caddy reverse proxy (port 8800, internal)
       -> web        (React/Next.js frontend, port 3000)
       -> admin      (Admin dashboard, port 3000)
       -> space      (Public space, port 3000)
       -> api        (Django REST API, port 8000)
       -> live       (WebSocket collaboration, port 3000)
       -> plane-minio (S3-compatible file storage, port 9000)

api -> plane-db     (PostgreSQL 15.7)
api -> plane-redis  (Valkey/Redis 7.2.11)
api -> plane-mq     (RabbitMQ 3.13.6)
api -> /app/kb      (Knowledge base volume, read-only mount from /git/funding-cockpit/kb)
api -> OpenClaw     (AI chat gateway at 172.18.0.1:18789)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python/Django 4.2 + Django REST Framework |
| Frontend | React + TypeScript (Vite/React Router) |
| Database | PostgreSQL 15.7 |
| Cache | Redis (Valkey 7.2.11) |
| Message Queue | RabbitMQ 3.13.6 |
| File Storage | MinIO (S3-compatible) |
| Reverse Proxy | Caddy (internal) + nginx (external, SSL) |
| AI Chat | OpenClaw WebSocket gateway |
| Auth | Magic link (email code, JWT sessions) |

## Comparison: Old vs New

| Feature | Old (FastAPI + Alpine.js) | New (Plane-Based) |
|---------|--------------------------|-------------------|
| **Pipeline/Kanban** | Custom 12-phase board | Plane's native board + custom 12 states |
| **Calendar** | Custom calendar view | Plane's built-in calendar layout |
| **Task Management** | None (opportunities only) | Full issues, subtasks, assignees, cycles, modules |
| **Gantt/Timeline** | None | Plane's built-in timeline view |
| **Spreadsheet View** | None | Plane's built-in spreadsheet layout |
| **Knowledge Base** | Custom file tree browser | Mounted volume + custom API endpoints + Plane Pages |
| **AI Chat** | WebSocket (OpenClaw) | REST API proxy (OpenClaw) |
| **Activity Logging** | JSON activity_log field | Both Plane's native + FundingActivityLog model |
| **Proposal Tracking** | None | Proposal model (draft -> review -> submitted -> accepted/rejected) |
| **Partner Management** | None | Partner + ConsortiumMember models |
| **Meeting Tracking** | None | Meeting model (internal, partner, info day, review, kickoff) |
| **Implementation Milestones** | None | ImplementationMilestone model with deliverables |
| **Multi-Tenant** | Single tenant | Workspace isolation (one per company) |
| **Real-time Collaboration** | None | Plane's live server (WebSocket) |
| **File Attachments** | Linked docs (path refs) | MinIO storage + linked docs preserved |
| **Search** | Full-text .md/.txt | Full-text .md/.txt + Plane's native search |
| **User Management** | Allowed emails list | Full RBAC (admin, member, guest) |
| **Database** | JSON file (opportunities.json) | PostgreSQL |
| **Deployment** | Single Docker container | 12 containers (docker-compose) |

## Data Migrated

| Data | Count | Notes |
|------|-------|-------|
| Opportunities | 160 (151 imported + 9 seed) | All phases, priorities, assignees preserved |
| Activity Logs | 118 | Historical change tracking |
| Linked Documents | 148 opportunities with 341 refs | Stored as JSON paths, resolved via KB endpoint |
| KB Files | 418 files (125 MB) | Mounted read-only from old cockpit |
| Projects (_index.md) | 18 across 3 categories | Full Match, ESR Only, Proposal Only |
| Labels | 13 normalized from 34 type variants | Horizon Europe, Cascade, Digital Europe, etc. |
| Pipeline States | 12 | Backlog -> Discovery -> ... -> Won/Rejected/Archived |

## Custom Funding Extension

Located in `apps/api/plane/funding/`. Registered in `INSTALLED_APPS` as `plane.funding`.

### Models (`models.py`)

- **FundingOpportunity** -- 1:1 linked to Plane Issue. Fields: external_id, opportunity_type, budget, relevance (1-5), fit_notes, source, url, call_id, next_step, deadline, linked_docs (JSON), tags (JSON)
- **FundingActivityLog** -- Change tracking per opportunity
- **Proposal** -- Draft/review/submission tracking per opportunity
- **Partner** -- Workspace-scoped partner directory (org type, country, contact, expertise)
- **ConsortiumMember** -- Links partner to opportunity with role (coordinator, partner, subcontractor)
- **Meeting** -- Meeting/call tracking per opportunity (internal, partner, info day, review, kickoff)
- **ImplementationMilestone** -- Post-award deliverable tracking with status and due dates

### API Endpoints (27 total)

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

**AI Chat:**
```
POST /workspaces/{slug}/projects/{id}/funding/chat/send/
GET  /workspaces/{slug}/projects/{id}/funding/chat/history/
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
```

## Multi-Tenant

Each company gets its own **Plane workspace** with full data isolation. Users can belong to multiple workspaces and switch between them via the workspace dropdown.

To add a second company:
```bash
docker compose -p funding-plane exec api python manage.py create_tenant \
  --name "Other Company" --slug other-company --admin user@other.com
```

This creates a workspace with the standard 12-phase pipeline, type labels, and a "EU Funding Pipeline" project.

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

### Environment Files

- `.env` -- Root env (PostgreSQL, Redis, RabbitMQ, MinIO credentials, ports)
- `apps/api/.env` -- API env (database URL, SMTP, OpenClaw, base URLs, auth config)
- `apps/web/.env` -- Frontend env (API base URL)
- `apps/admin/.env`, `apps/space/.env`, `apps/live/.env` -- Service-specific env

### Key Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `KB_PATH` | Knowledge base directory mount | `/app/kb` |
| `OPENCLAW_API_URL` | AI chat gateway URL | `http://172.18.0.1:18789` |
| `OPENCLAW_TOKEN` | AI chat auth token | (required) |
| `OPENCLAW_SESSION_KEY` | Chat session identifier | `agent:main:webchat:funding-cockpit-chat` |
| `EMAIL_HOST` | SMTP server for magic link | `smtp.easyname.eu` |
| `EMAIL_HOST_USER` | SMTP username | `worker1.kiss@kiss-it.io` |
| `SKIP_ENV_VAR` | Read config from env vars (0) or DB (1) | `0` |
| `ENABLE_SIGNUP` | Allow new user registration | `1` |
| `ENABLE_MAGIC_LINK_LOGIN` | Enable email code login | `1` |

## Infrastructure

- **Server:** Hetzner CX43 VPS (46.225.111.79)
- **SSL:** Let's Encrypt via certbot, managed by nginx
- **nginx config:** `/etc/nginx/sites-enabled/plane.46.225.111.79.nip.io`
- **Docker project:** `funding-plane`
- **KB data:** Mounted from `/git/funding-cockpit/kb` (shared with old cockpit, read-only)
- **Old cockpit:** Still running at `funding-cockpit-app-1` on port 8101 (https://funding.kiss-it.io)

## Repository Structure

```
apps/
  api/                          # Django backend
    plane/
      funding/                  # Custom funding extension
        models.py               # FundingOpportunity, Proposal, Partner, etc.
        views.py                # Pipeline, Dashboard, CRUD views
        views_kb.py             # Knowledge Base file serving
        views_chat.py           # AI Chat (OpenClaw proxy)
        views_projects.py       # Projects view (_index.md parser)
        serializers.py          # DRF serializers
        urls.py                 # All funding API routes
        management/commands/
          seed_funding_data.py  # Initial data seeding
          import_opportunities.py # Full production data import
          create_tenant.py      # Multi-tenant workspace setup
        migrations/
          0001_initial.py
          0002_fundingopportunity_linked_docs_and_more.py
  web/                          # React frontend (Plane UI)
  admin/                        # Admin dashboard
  space/                        # Public sharing
  live/                         # Real-time collaboration (WebSocket)
  proxy/                        # Caddy reverse proxy
```

## Based On

[Plane](https://github.com/makeplane/plane) -- AGPL-3.0 licensed open-source project management.
