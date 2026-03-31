"""AI Chat endpoint — proxies to OpenClaw WebSocket gateway.

Provides a REST POST interface to send messages to the AI assistant
and receive responses synchronously.
"""

import asyncio
import json
import os
import uuid
from urllib.parse import urlparse

from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView

try:
    import websockets
except ImportError:
    websockets = None


OPENCLAW_API_URL = os.environ.get(
    "OPENCLAW_API_URL", "http://172.18.0.1:18789"
)
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "")
OPENCLAW_SESSION_KEY = os.environ.get(
    "OPENCLAW_SESSION_KEY",
    "agent:main:webchat:funding-cockpit-chat",
)
OPENCLAW_TIMEOUT_SECONDS = float(
    os.environ.get("OPENCLAW_TIMEOUT_SECONDS", "45")
)


def _openclaw_ws_url():
    parsed = urlparse(OPENCLAW_API_URL)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return parsed._replace(
        scheme=scheme,
        path=parsed.path or "/",
        params="",
        query="",
        fragment="",
    ).geturl()


def _message_text(parts):
    texts = []
    for part in parts or []:
        if part.get("type") == "text" and part.get("text"):
            texts.append(part["text"])
    return "\n\n".join(texts).strip()


def _latest_assistant_message(history):
    messages = history.get("messages") or []
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return message
    return None


async def _rpc_request(ws, method, params):
    request_id = str(uuid.uuid4())
    await ws.send(
        json.dumps(
            {
                "type": "req",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
    )
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") == "res" and msg.get("id") == request_id:
            if not msg.get("ok"):
                raise RuntimeError(
                    msg.get("error", {}).get("message")
                    or f"OpenClaw RPC {method} failed"
                )
            return msg.get("payload") or {}


async def _fetch_chat_history(ws):
    return await _rpc_request(
        ws,
        "chat.history",
        {"sessionKey": OPENCLAW_SESSION_KEY, "limit": 20},
    )


async def _send_to_openclaw(message, user_email):
    """Send message to OpenClaw and wait for assistant response."""
    if not OPENCLAW_TOKEN:
        return "AI chat token is not configured."

    ws_url = _openclaw_ws_url()
    connect_params = {
        "minProtocol": 3,
        "maxProtocol": 3,
        "client": {
            "id": "openclaw-control-ui",
            "version": "funding-cockpit-plane",
            "platform": "python",
            "mode": "webchat",
        },
        "role": "operator",
        "scopes": ["operator.read", "operator.write"],
        "caps": ["tool-events"],
        "auth": {"token": OPENCLAW_TOKEN},
        "userAgent": "funding-cockpit-plane",
        "locale": "en-US",
    }
    chat_message = f"[Funding Cockpit Chat] [{user_email}] {message}"

    try:
        async with websockets.connect(
            ws_url,
            origin=OPENCLAW_API_URL,
            max_size=2**22,
            open_timeout=OPENCLAW_TIMEOUT_SECONDS,
            close_timeout=OPENCLAW_TIMEOUT_SECONDS,
        ) as ws:
            await ws.recv()  # connect.challenge
            await _rpc_request(ws, "connect", connect_params)

            history_before = await _fetch_chat_history(ws)
            last_assistant = _latest_assistant_message(history_before)
            last_id = (
                (last_assistant or {}).get("__openclaw") or {}
            ).get("id")

            await _rpc_request(
                ws,
                "chat.send",
                {
                    "sessionKey": OPENCLAW_SESSION_KEY,
                    "message": chat_message,
                    "deliver": False,
                    "attachments": [],
                    "idempotencyKey": str(uuid.uuid4()),
                },
            )

            for _ in range(60):
                history_after = await _fetch_chat_history(ws)
                assistant_msg = _latest_assistant_message(history_after)
                assistant_id = (
                    (assistant_msg or {}).get("__openclaw") or {}
                ).get("id")
                assistant_text = _message_text(
                    (assistant_msg or {}).get("content") or []
                )
                if (
                    assistant_id
                    and assistant_id != last_id
                    and assistant_text
                ):
                    return assistant_text
                await asyncio.sleep(0.5)

            return "The AI service did not respond in time."

    except Exception as e:
        return f"Error connecting to AI service: {e}"


class ChatSendView(BaseAPIView):
    """POST a message to the AI chat and receive the response."""

    def post(self, request, slug, project_id):
        if websockets is None:
            return Response(
                {"error": "websockets package not installed"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        message = request.data.get("message", "").strip()
        if not message:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_email = request.user.email
        loop = asyncio.new_event_loop()
        try:
            response_text = loop.run_until_complete(
                _send_to_openclaw(message, user_email)
            )
        finally:
            loop.close()

        return Response(
            {
                "message": message,
                "response": response_text,
                "user": user_email,
            }
        )


class ChatHistoryView(BaseAPIView):
    """GET recent chat history from OpenClaw."""

    def get(self, request, slug, project_id):
        if websockets is None:
            return Response(
                {"error": "websockets package not installed"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        async def _get_history():
            if not OPENCLAW_TOKEN:
                return {"messages": []}

            ws_url = _openclaw_ws_url()
            connect_params = {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "openclaw-control-ui",
                    "version": "funding-cockpit-plane",
                    "platform": "python",
                    "mode": "webchat",
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write"],
                "caps": ["tool-events"],
                "auth": {"token": OPENCLAW_TOKEN},
                "userAgent": "funding-cockpit-plane",
                "locale": "en-US",
            }
            try:
                async with websockets.connect(
                    ws_url,
                    origin=OPENCLAW_API_URL,
                    max_size=2**22,
                    open_timeout=10,
                    close_timeout=10,
                ) as ws:
                    await ws.recv()
                    await _rpc_request(ws, "connect", connect_params)
                    history = await _fetch_chat_history(ws)
                    messages = []
                    for msg in history.get("messages", []):
                        text = _message_text(msg.get("content") or [])
                        if text:
                            messages.append(
                                {
                                    "role": msg.get("role", "unknown"),
                                    "content": text,
                                }
                            )
                    return {"messages": messages}
            except Exception as e:
                return {"messages": [], "error": str(e)}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(_get_history())
        finally:
            loop.close()

        return Response(result)
