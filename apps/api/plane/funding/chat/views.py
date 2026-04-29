"""HTTP endpoints for the funding chat backed by the local claude CLI.

Three endpoints:

  GET    .../funding/chat/sessions/                       — list current user's sessions
  POST   .../funding/chat/sessions/                       — create a new session
  GET    .../funding/chat/sessions/<id>/messages/         — paginated history (Postgres)
  POST   .../funding/chat/sessions/<id>/messages/         — send a message; SSE stream of deltas
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from decimal import Decimal

from django.db import transaction
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.db.models import Workspace

from ..models import FundingChatMessage, FundingChatSession
from . import runner

logger = logging.getLogger("plane.funding.chat")

MAX_INPUT_CHARS = 4000
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean_input(raw: str) -> str:
    text = (raw or "").strip()
    text = CONTROL_CHARS_RE.sub("", text)
    return text[:MAX_INPUT_CHARS]


def _serialize_session(s: FundingChatSession) -> dict:
    return {
        "id": str(s.id),
        "claude_session_id": str(s.claude_session_id),
        "title": s.title,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _serialize_message(m: FundingChatMessage) -> dict:
    return {
        "id": str(m.id),
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
        "tokens_in": m.tokens_in,
        "tokens_out": m.tokens_out,
        "cost_usd": float(m.cost_usd) if m.cost_usd is not None else None,
    }


class ChatSessionsView(BaseAPIView):
    """List or create chat sessions for the current user in this workspace."""

    throttle_scope = "funding_chat"

    def get(self, request, slug, project_id):
        workspace = get_object_or_404(Workspace, slug=slug)
        sessions = FundingChatSession.objects.filter(
            workspace=workspace, user=request.user
        ).order_by("-updated_at")[:50]
        return Response({"sessions": [_serialize_session(s) for s in sessions]})

    def post(self, request, slug, project_id):
        workspace = get_object_or_404(Workspace, slug=slug)
        title = (request.data.get("title") or "").strip()[:200]
        session = FundingChatSession.objects.create(
            workspace=workspace,
            user=request.user,
            claude_session_id=uuid.uuid4(),
            title=title,
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(_serialize_session(session), status=status.HTTP_201_CREATED)


class ChatMessagesView(BaseAPIView):
    """List history (GET) or send a new message and stream the reply (POST)."""

    throttle_scope = "funding_chat"

    def get(self, request, slug, project_id, session_id):
        session = get_object_or_404(
            FundingChatSession, id=session_id, user=request.user
        )
        messages = list(session.messages.order_by("created_at"))
        return Response({"messages": [_serialize_message(m) for m in messages]})

    def post(self, request, slug, project_id, session_id):
        session = get_object_or_404(
            FundingChatSession, id=session_id, user=request.user
        )
        message = _clean_input(request.data.get("message", ""))
        if not message:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Persist the user turn synchronously so it's never lost.
        with transaction.atomic():
            user_msg = FundingChatMessage.objects.create(
                session=session,
                role="user",
                content=message,
                created_by=request.user,
                updated_by=request.user,
            )
            had_prior_turns = session.messages.filter(role="assistant").exists()
            session.save(update_fields=["updated_at"])

        return StreamingHttpResponse(
            _stream_response(session, message, resume=had_prior_turns, user_msg=user_msg, user=request.user),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )


def _sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


def _stream_response(session, prompt, *, resume, user_msg, user):
    """Generator pumped to the client by ``StreamingHttpResponse``.

    Iterates the synchronous ``runner.stream_claude`` generator, fans out
    text deltas as SSE ``delta`` events, captures token+cost from the final
    ``result`` event, and persists the assistant message to Postgres at end
    of stream.
    """
    accumulated_text: list[str] = []
    raw_events: list[dict] = []
    tokens_in = tokens_out = None
    cost_usd: Decimal | None = None

    yield _sse({"type": "open", "session_id": str(session.id)})

    try:
        for event in runner.stream_claude(
            prompt, session_id=str(session.claude_session_id), resume=resume
        ):
            raw_events.append(event)

            # Surface upstream errors directly to the user.
            if isinstance(event, dict) and event.get("type") == "error":
                yield _sse({"type": "error", "message": str(event.get("message") or "claude error")})
                continue

            delta = runner.extract_text_delta(event)
            if delta:
                accumulated_text.append(delta)
                yield _sse({"type": "delta", "text": delta})

            t_in, t_out, cost = runner.extract_usage(event)
            if t_in is not None:
                tokens_in = t_in
            if t_out is not None:
                tokens_out = t_out
            if cost is not None:
                cost_usd = Decimal(str(cost))
    except runner.ClaudeError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception:  # pragma: no cover  defensive
        logger.exception("chat.stream_failed")
        yield _sse({"type": "error", "message": "internal error"})

    final_text = "".join(accumulated_text).strip()
    if final_text:
        with transaction.atomic():
            assistant_msg = FundingChatMessage.objects.create(
                session=session,
                role="assistant",
                content=final_text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                raw={"events": raw_events[-50:]},  # last 50 events for debugging
                created_by=user,
                updated_by=user,
            )
            if not session.title:
                session.title = (final_text[:60] or prompt[:60]).strip()
                session.save(update_fields=["title", "updated_at"])
            else:
                session.save(update_fields=["updated_at"])

        yield _sse(
            {
                "type": "done",
                "message_id": str(assistant_msg.id),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": float(cost_usd) if cost_usd is not None else None,
            }
        )
    else:
        yield _sse({"type": "done", "message_id": None})
