"""Unit tests for the chat runner.

Now that the runner is a thin HTTP client around the host claude-exec
server we focus on:

- The two helper functions that decode stream-json events
  (``extract_text_delta`` / ``extract_usage``)
- The guard that refuses to call out without a configured token

Network calls are not exercised here — the host server's smoke test in
docs/RUNBOOK.md covers the live path.
"""

import pytest

from plane.funding.chat import runner


def test_extract_text_delta_from_stream_event():
    event = {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "hello"},
        },
    }
    assert runner.extract_text_delta(event) == "hello"


def test_extract_text_delta_returns_none_for_unrelated():
    assert runner.extract_text_delta({"foo": "bar"}) is None
    assert runner.extract_text_delta({"type": "stream_event", "event": {"type": "message_start"}}) is None
    assert runner.extract_text_delta(None) is None  # type: ignore[arg-type]


def test_extract_usage_from_result():
    event = {
        "type": "result",
        "usage": {"input_tokens": 10, "output_tokens": 20},
        "total_cost_usd": 0.0042,
    }
    assert runner.extract_usage(event) == (10, 20, 0.0042)


def test_extract_usage_other_event_returns_none():
    assert runner.extract_usage({"type": "stream_event"}) == (None, None, None)


def test_stream_claude_requires_token(monkeypatch):
    monkeypatch.setattr(runner, "CLAUDE_EXEC_TOKEN", "")
    with pytest.raises(runner.ClaudeError):
        # Iterate to trigger the generator body.
        list(runner.stream_claude("hi", session_id="00000000-0000-0000-0000-000000000000", resume=False))
