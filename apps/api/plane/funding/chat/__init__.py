"""Funding chat backend powered by the local Anthropic Claude CLI.

Replaces the old OpenClaw WebSocket gateway. The CLI is installed into the
api docker image (see ``apps/api/Dockerfile.api``) and shelled out to per
request. Multi-turn context is preserved via ``--session-id`` / ``--resume``;
user-facing history is persisted in Postgres via ``FundingChatSession`` and
``FundingChatMessage``.
"""
