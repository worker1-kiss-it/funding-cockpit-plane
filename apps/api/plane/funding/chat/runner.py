"""HTTP client for the host-side claude-exec-server.

The api container intentionally does NOT bundle the ``claude`` CLI or an
Anthropic API key. Instead it POSTs each chat turn to a small server running
on the docker host as the user that owns ``~/.claude/`` (typically
``clauderunner``), which shells out to the locally-installed,
OAuth-authenticated CLI and streams ``--output-format stream-json`` events
back as NDJSON.

This module:

- POSTs the prompt to ``CLAUDE_EXEC_URL/v1/chat`` with a bearer token
- Reads the chunked NDJSON response line-by-line, decoding each line into a
  ``dict`` event the chat view can persist + replay over SSE
- Provides ``extract_text_delta`` / ``extract_usage`` helpers used by the
  view to pull human text and token/cost info out of the stream
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterator
from urllib import error as urllib_error
from urllib import request as urllib_request

from .system_prompt import SYSTEM_PROMPT

logger = logging.getLogger("plane.funding.chat")

CLAUDE_EXEC_URL = os.environ.get("CLAUDE_EXEC_URL", "http://host.docker.internal:5557").rstrip("/")
CLAUDE_EXEC_TOKEN = os.environ.get("CLAUDE_EXEC_TOKEN", "")
CLAUDE_TIMEOUT = float(os.environ.get("CLAUDE_TIMEOUT_SECONDS", "180"))


class ClaudeError(RuntimeError):
    pass


def stream_claude(prompt: str, *, session_id: str, resume: bool) -> Iterator[dict]:
    """POST to the host claude-exec server and yield each NDJSON event.

    Iteration is bounded by ``CLAUDE_TIMEOUT_SECONDS``; the host server
    enforces its own (tighter) timeout as well. Network/HTTP errors are
    re-raised as :class:`ClaudeError` so the view can persist a system
    message and tell the user what happened.
    """
    if not CLAUDE_EXEC_TOKEN:
        raise ClaudeError("CLAUDE_EXEC_TOKEN is not configured in the api container env")

    body = json.dumps(
        {
            "prompt": prompt,
            "session_id": session_id,
            "resume": resume,
            "system_prompt": SYSTEM_PROMPT,
        }
    ).encode("utf-8")

    req = urllib_request.Request(
        f"{CLAUDE_EXEC_URL}/v1/chat",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {CLAUDE_EXEC_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/x-ndjson",
        },
    )

    try:
        # urllib's HTTPResponse iterator doesn't honour chunked transfer
        # framing reliably, so we iterate by line ourselves.
        response = urllib_request.urlopen(req, timeout=CLAUDE_TIMEOUT)
    except urllib_error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise ClaudeError(f"claude-exec HTTP {exc.code}: {body_text[:500]}") from exc
    except urllib_error.URLError as exc:
        raise ClaudeError(f"claude-exec unreachable: {exc.reason}") from exc

    try:
        with response:
            for raw_line in response:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("claude.bad_json: %r", line[:200])
    except TimeoutError as exc:
        raise ClaudeError("claude-exec stream timed out") from exc


# ---------------------------------------------------------------------------
# Event helpers (consumed by chat/views.py)


def extract_text_delta(event: dict) -> str | None:
    """Pull a textual delta out of a stream-json event, if any.

    The exec server passes through claude's stream-json wire format
    unchanged, plus our own ``open`` / ``exit`` / ``error`` envelope events.
    Two cases produce visible text:

    - ``stream_event`` → ``content_block_delta`` → ``text_delta``
    - ``assistant`` messages with a fully-formed text content block (we
      ignore these to avoid double-counting deltas).
    """
    if not isinstance(event, dict):
        return None

    if event.get("type") == "stream_event":
        inner = event.get("event") or {}
        if inner.get("type") == "content_block_delta":
            delta = inner.get("delta") or {}
            if delta.get("type") == "text_delta":
                return delta.get("text") or ""
    return None


def extract_usage(event: dict) -> tuple[int | None, int | None, float | None]:
    """Pull token + cost info from a final ``result`` event."""
    if not isinstance(event, dict):
        return None, None, None
    if event.get("type") == "result":
        usage = event.get("usage") or {}
        return (
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            event.get("total_cost_usd"),
        )
    return None, None, None
