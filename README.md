# Funding Cockpit (Plane-Based)

Central management platform for EU funding opportunities, built on top of [Plane](https://plane.so/) (open-source project management). Extends Plane with funding-specific models, a knowledge base, AI chat, partner/consortium management, proposal tracking, and a two-project task workflow.

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

| Project | Identifier | Purpose |
|---------|-----------|---------|
| **EU Funding Pipeline** | FUND | Opportunities only -- clean kanban pipeline board |
| **Funding Tasks** | TASK | Action items, deliverables, to-dos linked to opportunities |

**Why two projects?** Sub-work items in Plane appear as standalone cards on the board, cluttering the pipeline view. Keeping opportunities and tasks in separate projects keeps the pipeline clean while allowing full task management.

**How to create a task for an opportunity:**
1. Open any opportunity (e.g. FUND-146 GenAI-Cybersecure EU)
2. Click **"Create task"** button (in the action bar next to "Add sub-work item", "Add relation", etc.)
3. Enter a task name -- the task is created in the TASK project with an automatic `relates_to` relation back to the opportunity
4. The relation is visible on both sides (opportunity shows linked tasks, task shows linked opportunity)

## Architecture

```
nginx (ports 80/443, Let's Encrypt SSL)
  -> Caddy reverse proxy (port 8800, internal only)
       -> web        (React frontend, port 3000)
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
| **Pipeline/Kanban** | Custom 12-phase board | Plane native board + 12 custom states |
| **Calendar** | Custom calendar view | Plane built-in calendar layout |
| **Task Management** | None | Separate TASK project with linked tasks |
| **Gantt/Timeline** | None | Plane built-in timeline view |
| **Spreadsheet View** | None | Plane built-in spreadsheet layout |
| **Knowledge Base** | Custom file tree browser | Custom KB browser page in Plane sidebar |
| **AI Chat** | WebSocket sidebar | Dark-themed slide-out drawer with OpenClaw |
| **Funding Dashboard** | Custom stats page | Custom dashboard page in Plane sidebar |
| **Activity Logging** | JSON field | Plane native + FundingActivityLog model |
| **Proposal Tracking** | None | Proposal model on issue detail sidebar |
| **Partner Management** | None | Partner + ConsortiumMember on issue detail |
| **Meeting Tracking** | None | Meeting model on issue detail sidebar |
| **Implementation Milestones** | None | ImplementationMilestone on issue detail |
| **Multi-Tenant** | Single tenant | Workspace isolation (one per company) |
| **Real-time Collaboration** | None | Plane live server (WebSocket) |
| **File Attachments** | Linked doc paths | MinIO storage + linked docs preserved |
| **Search** | Full-text .md/.txt | Full-text KB search + Plane native search |
| **User Management** | Allowed emails list | Full RBAC (admin, member, guest) |
| **Saved Views / Quick Links** | None | Favorited views in sidebar (board, calendar, etc.) |
| **Dark Mode** | Custom dark theme | Plane native dark mode (default) |
| **Database** | JSON file | PostgreSQL |

## Frontend Extensions (Plane UI)

All custom frontend code uses Plane's CE (Community Edition) extension system, keeping customizations cleanly separated from core code.

### Sidebar Navigation
- **Funding Dashboard** -- stats cards, phase distribution, upcoming deadlines table
- **Knowledge Base** -- file tree browser with 418 files, markdown rendering, PDF/image viewer, search

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
- Loads chat history from OpenClaw
- Send messages, receive AI responses
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
- Added as member to the FUND project

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

### API Endpoints (28 total)

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
  api/                              # Django backend
    plane/
      funding/                      # Custom funding extension
        apps.py                     # AppConfig with signal registration
        models.py                   # FundingOpportunity, Proposal, Partner, etc.
        signals.py                  # Auto-provision defaults for new users
        views.py                    # Pipeline, Dashboard, CRUD, CreateLinkedTask
        views_kb.py                 # Knowledge Base file serving
        views_chat.py               # AI Chat (OpenClaw proxy)
        views_projects.py           # Projects view (_index.md parser)
        serializers.py              # DRF serializers
        urls.py                     # All funding API routes (28 endpoints)
        management/commands/
          seed_funding_data.py      # Initial data seeding
          import_opportunities.py   # Full production data import
          create_tenant.py          # Multi-tenant workspace setup
        migrations/
          0001_initial.py
          0002_fundingopportunity_linked_docs_and_more.py
  web/                              # React frontend (Plane UI)
    core/
      services/
        funding.service.ts          # FundingService API client (all endpoints)
    ce/
      store/
        funding/                    # MobX stores (dashboard, kb, chat, opportunity)
        root.store.ts               # Extended with FundingStore
      components/
        funding/
          dashboard/index.tsx       # Funding Dashboard page
          kb/index.tsx              # Knowledge Base browser page
          chat/index.tsx            # AI Chat floating drawer
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
  proxy/                            # Caddy reverse proxy
packages/
  constants/src/workspace.ts        # Sidebar nav items (funding_dashboard, knowledge_base)
  i18n/src/locales/en/translations.ts  # Labels for sidebar items
```

## Based On

[Plane](https://github.com/makeplane/plane) -- AGPL-3.0 licensed open-source project management (~209K lines of code, ~144 contributors, est. 40-60K developer hours).
