"""Tests for the chat view input sanitisation."""

from plane.funding.chat.views import _clean_input, MAX_INPUT_CHARS


def test_strips_control_chars():
    assert _clean_input("hello\x00world") == "helloworld"
    assert _clean_input("a\x07b") == "ab"


def test_caps_length():
    big = "x" * (MAX_INPUT_CHARS + 100)
    cleaned = _clean_input(big)
    assert len(cleaned) == MAX_INPUT_CHARS


def test_strips_whitespace():
    assert _clean_input("  hi  ") == "hi"


def test_empty_input():
    assert _clean_input("") == ""
    assert _clean_input(None) == ""  # type: ignore[arg-type]
