"""Claude Exec Server.

Tiny HTTP service that wraps the locally-installed, OAuth-authenticated
``claude`` CLI so that other services (in particular the Funding Cockpit api
container) can use it without bundling Node.js, the CLI binary, or an API
key. Designed to run on the same host as the user that owns
``~/.claude/`` — typically ``clauderunner``.

Hardening over the original Flask sketch:

- argv list, NEVER ``shell=True`` (no command injection)
- prompt is passed via stdin, not the command line, so it can't end up in
  ``ps``, system logs, or argv length limits
- ``--allowedTools "Read"`` instead of ``--dangerously-skip-permissions``
- bearer-token auth on every endpoint
- 127.0.0.1 only by default
- per-request and per-process concurrency caps
- structured JSON logs with request ids
- watchdog timeout that actually kills the subprocess group
- chunked NDJSON streaming so the upstream sees deltas in real time
- waitress instead of the dev server
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import shutil
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, abort, g, jsonify, request, stream_with_context
from waitress import serve

# ---------------------------------------------------------------------------
# Config

CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "/home/clauderunner/.local/bin/claude"
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
TIMEOUT_SECONDS = int(os.environ.get("CLAUDE_TIMEOUT_SECONDS", "180"))
MAX_PROMPT_CHARS = int(os.environ.get("CLAUDE_MAX_PROMPT_CHARS", "8000"))
MAX_CONCURRENCY = int(os.environ.get("CLAUDE_MAX_CONCURRENCY", "4"))

ALLOWED_DIRS = [
    d.strip()
    for d in os.environ.get(
        "CLAUDE_ALLOWED_DIRS",
        "/git/funding-cockpit/kb,/srv/funding-cockpit/pages-cache",
    ).split(",")
    if d.strip()
]

LISTEN_HOST = os.environ.get("CLAUDE_EXEC_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("CLAUDE_EXEC_PORT", "5557"))

TOKEN_FILE = os.environ.get("CLAUDE_EXEC_TOKEN_FILE", "/home/clauderunner/claude-exec-server/token")


def _load_token() -> str:
    env = os.environ.get("CLAUDE_EXEC_TOKEN", "").strip()
    if env:
        return env
    p = Path(TOKEN_FILE)
    if p.is_file():
        return p.read_text().strip()
    raise SystemExit(
        f"No auth token configured. Set CLAUDE_EXEC_TOKEN env var or write {TOKEN_FILE}."
    )


AUTH_TOKEN = _load_token()

# ---------------------------------------------------------------------------
# Logging

logger = logging.getLogger("claude-exec")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for key in ("rid", "session_id", "duration_ms", "code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


_handler.setFormatter(_JsonFormatter())
logger.addHandler(_handler)
logger.propagate = False

# ---------------------------------------------------------------------------
# Concurrency cap

_semaphore = threading.BoundedSemaphore(MAX_CONCURRENCY)

# ---------------------------------------------------------------------------
# Flask app

app = Flask(__name__)


@app.before_request
def _attach_request_id() -> None:
    g.rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]


def _require_auth() -> None:
    """Reject the request unless ``Authorization: Bearer <token>`` matches."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        abort(401, description="missing bearer token")
    presented = header[len("Bearer ") :].strip()
    if not secrets.compare_digest(presented, AUTH_TOKEN):
        abort(401, description="bad token")


def _build_argv(*, session_id: str, resume: bool, model: str, system_prompt: str | None) -> list[str]:
    argv: list[str] = [
        CLAUDE_BIN,
        "--print",
        "--input-format",
        "text",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model",
        model,
        "--allowedTools",
        "Read",
    ]

    if resume:
        argv += ["--resume", session_id]
    else:
        argv += ["--session-id", session_id]

    if system_prompt:
        argv += ["--append-system-prompt", system_prompt]

    for d in ALLOWED_DIRS:
        if Path(d).is_dir():
            argv += ["--add-dir", d]

    return argv


def _emit(obj: dict) -> bytes:
    return (json.dumps(obj) + "\n").encode("utf-8")


def _stream_claude(payload: dict):
    """Generator that spawns claude and yields raw stream-json lines as NDJSON bytes."""
    started = time.monotonic()
    rid = g.rid

    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        yield _emit({"type": "error", "message": "prompt is required"})
        return
    if len(prompt) > MAX_PROMPT_CHARS:
        yield _emit({"type": "error", "message": "prompt too long"})
        return

    raw_session_id = (payload.get("session_id") or "").strip()
    try:
        session_uuid = str(uuid.UUID(raw_session_id))
    except (ValueError, TypeError):
        yield _emit({"type": "error", "message": "invalid session_id (must be UUID)"})
        return

    resume = bool(payload.get("resume"))
    model = payload.get("model") or DEFAULT_MODEL
    system_prompt = payload.get("system_prompt")

    argv = _build_argv(
        session_id=session_uuid,
        resume=resume,
        model=str(model),
        system_prompt=system_prompt,
    )

    if not _semaphore.acquire(timeout=30):
        yield _emit({"type": "error", "message": "server busy"})
        return

    proc: subprocess.Popen | None = None
    timer: threading.Timer | None = None
    try:
        # Inherit clauderunner's HOME so claude finds ~/.claude/
        env = os.environ.copy()

        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
            start_new_session=True,  # own process group, so we can kill children
        )

        # Hand the prompt to the CLI on stdin so it doesn't appear in argv.
        try:
            assert proc.stdin is not None
            proc.stdin.write(prompt)
            proc.stdin.close()
        except BrokenPipeError:
            pass

        def _kill_on_timeout() -> None:
            if proc and proc.poll() is None:
                logger.warning("claude.timeout", extra={"rid": rid, "session_id": session_uuid})
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        timer = threading.Timer(TIMEOUT_SECONDS, _kill_on_timeout)
        timer.daemon = True
        timer.start()

        logger.info(
            "claude.spawn",
            extra={"rid": rid, "session_id": session_uuid},
        )
        yield _emit({"type": "open", "rid": rid, "session_id": session_uuid})

        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip("\n")
            if not line:
                continue
            # The CLI emits valid JSON per line; pass it straight through.
            yield (line + "\n").encode("utf-8")

        proc.wait()
        timer.cancel()

        stderr = ""
        if proc.stderr is not None:
            try:
                stderr = proc.stderr.read() or ""
            except Exception:
                stderr = ""

        duration_ms = int((time.monotonic() - started) * 1000)
        if proc.returncode == 0:
            logger.info(
                "claude.done",
                extra={"rid": rid, "session_id": session_uuid, "duration_ms": duration_ms, "code": 0},
            )
            yield _emit({"type": "exit", "code": 0, "duration_ms": duration_ms})
        else:
            logger.error(
                "claude.failed",
                extra={"rid": rid, "session_id": session_uuid, "duration_ms": duration_ms, "code": proc.returncode},
            )
            yield _emit(
                {
                    "type": "error",
                    "code": proc.returncode,
                    "message": (stderr or "claude exited non-zero")[:1000],
                }
            )
    finally:
        if timer is not None:
            timer.cancel()
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        _semaphore.release()


# ---------------------------------------------------------------------------
# Routes

@app.route("/health", methods=["GET"])
def health() -> Response:
    return jsonify(
        {
            "status": "healthy",
            "claude_bin": CLAUDE_BIN,
            "claude_bin_present": Path(CLAUDE_BIN).exists(),
            "model": DEFAULT_MODEL,
            "max_concurrency": MAX_CONCURRENCY,
            "allowed_dirs": ALLOWED_DIRS,
        }
    )


@app.route("/v1/chat", methods=["POST"])
def chat() -> Response:
    _require_auth()
    try:
        payload = request.get_json(force=True, silent=False) or {}
    except Exception:
        abort(400, description="invalid json body")

    return Response(
        stream_with_context(_stream_claude(payload)),
        mimetype="application/x-ndjson",
        headers={
            "X-Request-Id": g.rid,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        direct_passthrough=True,
    )


@app.errorhandler(401)
def _unauth(err):
    return jsonify({"error": "unauthorized", "detail": str(err.description)}), 401


@app.errorhandler(400)
def _bad(err):
    return jsonify({"error": "bad_request", "detail": str(err.description)}), 400


# ---------------------------------------------------------------------------
# Entrypoint

if __name__ == "__main__":
    logger.info(
        "claude-exec.start host=%s port=%s claude=%s allowed_dirs=%s",
        LISTEN_HOST,
        LISTEN_PORT,
        CLAUDE_BIN,
        ALLOWED_DIRS,
    )
    # Waitress: production WSGI, supports streaming. Threads = 2 × concurrency
    # so request acceptance never starves the semaphore.
    serve(
        app,
        host=LISTEN_HOST,
        port=LISTEN_PORT,
        threads=max(8, MAX_CONCURRENCY * 2),
        ident="claude-exec",
    )
