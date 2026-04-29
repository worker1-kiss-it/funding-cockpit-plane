# Funding Cockpit security model

This is the operational security doc for the Funding Cockpit deployment at
`https://plane.46.225.111.79.nip.io/`. The upstream Plane `SECURITY.md` covers
the framework's responsible-disclosure process; this file describes our
specific threat model and controls.

## Who is allowed in

- Authentication is **magic-link only** (no passwords, no OAuth).
- The instance has a small allow-list of email addresses; only listed users
  receive a code when they request a login. Adding a user is a manual
  operation done from the admin shell (see `docs/RUNBOOK.md` §9).
- All API endpoints require an authenticated session (`IsAuthenticated` is
  the DRF default and we never override it). The previous bypass on the KB
  raw-file endpoint has been removed and is regression-tested.

## Authorisation boundaries

- Workspace isolation is enforced by Plane: a user only sees workspaces they
  are a member of, and only projects they're a project member of within
  those workspaces.
- The funding chat endpoints scope sessions to `(workspace, user)` — a user
  cannot list or read another user's chat sessions.
- The Anthropic API key is **shared** across all users; users do not bring
  their own key. Cost is monitored via the per-message `cost_usd` field
  written by the chat backend.

## Data classification

| Data                                    | Sensitivity                           | Where it lives                                                                            |
| --------------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------- |
| Funding opportunity records             | Internal                              | Postgres (`funding_opportunities`)                                                        |
| KB markdown / PDFs                      | Internal                              | Filesystem (`/git/funding-cockpit/kb`) → being migrated to Plane Pages (Postgres + MinIO) |
| Chat history                            | Internal — may include strategy notes | Postgres (`funding_chat_messages`)                                                        |
| User magic-link codes                   | Sensitive (short-lived)               | Redis                                                                                     |
| Anthropic API key                       | Highly sensitive                      | `apps/api/.env`, never in git                                                             |
| Postgres + RabbitMQ + MinIO credentials | Highly sensitive                      | `apps/api/.env`, root `.env`, never in git                                                |

`apps/api/.env` and the root `.env` are gitignored. CI runs gitleaks on every
PR to make sure they stay that way.

## Network model

```
Internet → nginx (TLS termination, HSTS, Let's Encrypt)
        → Caddy (internal reverse proxy on 127.0.0.1:8800)
            → web / admin / space / api / live / minio
```

- nginx is the only thing bound to a public interface.
- Caddy listens on 127.0.0.1 — no external port.
- Postgres, Redis, RabbitMQ, and MinIO are not exposed outside the docker
  network.

Security headers added at the Caddy edge: HSTS, X-Content-Type-Options,
X-Frame-Options=SAMEORIGIN, Referrer-Policy=strict-origin-when-cross-origin,
Permissions-Policy disabling geolocation/microphone/camera. The `Server`
header is suppressed.

## Rate limiting

DRF `ScopedRateThrottle` is enabled in `apps/api/plane/settings/common.py`:

| Scope               | Rate         | Endpoints                            |
| ------------------- | ------------ | ------------------------------------ |
| `funding_chat`      | 30/min/user  | All chat session + message endpoints |
| `funding_kb_search` | 60/min/user  | KB search endpoint                   |
| `funding_kb_raw`    | 120/min/user | KB raw file download endpoint        |
| `anon`              | 30/min       | All anonymous traffic (default)      |

## Server-side AI chat

The chat backend shells out to the local `claude` CLI (Anthropic Claude Code,
pinned in `Dockerfile.api`). The runner enforces:

- **Tool allowlist**: only the `Read` tool is enabled (`--allowedTools "Read"`).
  Bash, Edit, WebFetch, and friends are blocked.
- **Working set whitelist**: only `/app/kb` and `/app/pages-cache` are exposed
  via `--add-dir`. The CLI cannot read anything else in the container.
- **Env scrubbing**: `_build_env()` only forwards `PATH`, `HOME`, locale,
  proxy vars, and `ANTHROPIC_API_KEY` — Django secrets, DB URLs, and
  workspace data are not in the subprocess env.
- **Concurrency cap**: `CLAUDE_MAX_CONCURRENCY` (default 5) bounds simultaneous
  CLI processes per worker via an `asyncio.Semaphore`.
- **Wall-clock timeout**: `CLAUDE_TIMEOUT_SECONDS` (default 120).
- **Input sanitisation**: messages are stripped of control chars and capped
  at 4 000 characters before reaching the CLI.

User-visible chat history is persisted in Postgres (`funding_chat_messages`);
the CLI's own session files live in the `claude_sessions` docker volume so
sessions survive restarts.

## Backups

Nightly backups are taken by `deployments/backups/backup.sh`:

- `pg_dump` of the `plane` database, gzipped + sha256-checksummed
- tar of the MinIO `/export` directory
- tar of the legacy KB filesystem (until decommissioned)

Restore procedure: `deployments/backups/RESTORE.md`.

## Monitoring

- **Sentry** (optional): set `SENTRY_DSN` and `SENTRY_ENVIRONMENT` in
  `apps/api/.env`; the api/worker/beat services initialise the SDK in
  `production.py`. Off by default to avoid surprise vendor lock-in.
- **Application logs** ship to stdout and are picked up by docker's logging
  driver. JSON-formatted via `python-json-logger`.

## CI / supply-chain

`.github/workflows/ci.yml` runs on every push and PR:

- `gitleaks` secret scan
- `ruff check plane/funding`
- `pytest plane/funding`
- `pnpm lint` + `pnpm typecheck` for the web app

`.pre-commit-config.yaml` mirrors the secret scan locally.

## Reporting a vulnerability

Email `g.kiss@kiss-it.io` with details. Do not file public issues for
security problems.
