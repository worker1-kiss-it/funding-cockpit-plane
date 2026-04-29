# Claude Exec Server (host-side)

A small HTTP service that wraps the locally-installed, OAuth-authenticated
`claude` CLI. The Funding Cockpit api container POSTs each chat turn to it
over the docker bridge. No Anthropic API key lives anywhere on disk —
authentication is whatever `claude login` set up under `~/.claude/`.

The server source lives outside this repo at `/home/clauderunner/claude-exec-server/`
on the production box (it stays out of the repo so the auth token never
brushes against git). This directory just holds the deploy artefacts:
the systemd unit, the ufw rules, and a reproducibility checklist.

## One-time install on a fresh host

Assumes a Debian/Ubuntu host with `clauderunner` user, the `claude` CLI
already installed and authenticated under `~clauderunner/.claude/`, and
ufw active.

```bash
# 1. Lay down the server
sudo -u clauderunner mkdir -p /home/clauderunner/claude-exec-server
sudo -u clauderunner python3 -m venv /home/clauderunner/claude-exec-server/venv
sudo -u clauderunner /home/clauderunner/claude-exec-server/venv/bin/pip install flask waitress
# Copy server.py from this repo's deployments/claude-exec/server.py (or
# regenerate it from the production box).
sudo -u clauderunner cp deployments/claude-exec/server.py /home/clauderunner/claude-exec-server/server.py

# 2. Generate the bearer token (and copy it into apps/api/.env as CLAUDE_EXEC_TOKEN)
sudo -u clauderunner python3 -c 'import secrets; print(secrets.token_urlsafe(48))' \
  | sudo -u clauderunner tee /home/clauderunner/claude-exec-server/token > /dev/null
sudo -u clauderunner chmod 600 /home/clauderunner/claude-exec-server/token

# 3. The bind-mounted page cache the chat assistant reads
sudo mkdir -p /srv/funding-cockpit/pages-cache
sudo chown -R clauderunner:clauderunner /srv/funding-cockpit

# 4. systemd user unit
sudo -u clauderunner mkdir -p /home/clauderunner/.config/systemd/user
sudo -u clauderunner cp deployments/claude-exec/claude-exec.service \
  /home/clauderunner/.config/systemd/user/claude-exec.service
sudo loginctl enable-linger clauderunner   # so the unit starts on boot
sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/$(id -u clauderunner) \
  systemctl --user daemon-reload
sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/$(id -u clauderunner) \
  systemctl --user enable --now claude-exec.service

# 5. ufw rules so the docker bridges can reach the host on 5557
sudo ufw allow from 172.17.0.0/16 to any port 5557 proto tcp comment "claude-exec docker0"
sudo ufw allow from 172.28.0.0/16 to any port 5557 proto tcp comment "claude-exec funding-plane bridge"

# 6. Smoke test
curl -s http://127.0.0.1:5557/health
TOKEN=$(sudo -u clauderunner cat /home/clauderunner/claude-exec-server/token)
curl -sN -X POST http://127.0.0.1:5557/v1/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Reply with exactly: HELLO_FROM_EXEC\",\"session_id\":\"$(uuidgen)\",\"resume\":false}"
```

## What it does and what it does NOT

- ✓ Reads `~clauderunner/.claude/` for auth — no API key on disk
- ✓ Spawns `claude --print --output-format stream-json --include-partial-messages` via argv list (no shell)
- ✓ Passes the prompt on stdin (never argv) so it doesn't hit `ps`/argv length limits
- ✓ `--allowedTools "Read"` only — Bash, Edit, WebFetch, etc. are blocked
- ✓ `--add-dir` whitelist (`/git/funding-cockpit/kb`, `/srv/funding-cockpit/pages-cache`) — the assistant cannot read anything outside those trees
- ✓ Bearer token auth on `/v1/chat`
- ✓ Concurrency cap (`CLAUDE_MAX_CONCURRENCY`) and watchdog kill on timeout
- ✓ Structured JSON logs to `/home/clauderunner/claude-exec-server/server.log`
- ✗ Does NOT proxy arbitrary commands. The only thing it can run is `claude` with the fixed flag set above; the request body's only effect is the prompt text and session id.

## Operational notes

- **Logs**: `tail -f /home/clauderunner/claude-exec-server/server.log`
- **Restart**: `sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/1001 systemctl --user restart claude-exec.service`
- **Status**: `sudo -u clauderunner XDG_RUNTIME_DIR=/run/user/1001 systemctl --user status claude-exec.service`
- **Rotate the bearer token**: rewrite `/home/clauderunner/claude-exec-server/token`, restart the unit, paste the new value into `apps/api/.env` as `CLAUDE_EXEC_TOKEN`, then `docker compose restart api worker`.
- **Re-auth claude**: run `claude` interactively as `clauderunner` once, complete the OAuth flow, then `systemctl --user restart claude-exec.service`.
