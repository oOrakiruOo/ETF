from __future__ import annotations

import json

import pytest

from src.line_engine import (
    build_line_broadcast_payload,
    build_line_push_payload,
    check_line_settings,
    send_line_broadcast_message,
    send_line_push_message,
)


def test_check_line_settings_masks_secret_values(monkeypatch) -> None:
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "secret-token")
    monkeypatch.delenv("LINE_TO_USER_ID", raising=False)

    assert check_line_settings() == {
        "LINE_CHANNEL_ACCESS_TOKEN": True,
        "LINE_TO_USER_ID": False,
    }


def test_build_line_push_payload_uses_text_message() -> None:
    payload = build_line_push_payload("U123", "ETF summary")

    assert payload == {
        "to": "U123",
        "messages": [{"type": "text", "text": "ETF summary"}],
    }


def test_build_line_broadcast_payload_uses_text_message() -> None:
    payload = build_line_broadcast_payload("ETF summary")

    assert payload == {
        "messages": [{"type": "text", "text": "ETF summary"}],
    }


def test_send_line_push_message_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("LINE_TO_USER_ID", "U123")

    with pytest.raises(RuntimeError, match="LINE_CHANNEL_ACCESS_TOKEN"):
        send_line_push_message("ETF summary")


def test_send_line_push_message_posts_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        status = 200

        def __enter__(self) -> "DummyResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request, timeout: int):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    status = send_line_push_message(
        "ETF summary",
        channel_access_token="token",
        to_user_id="U123",
    )

    assert status == 200
    assert captured["url"] == "https://api.line.me/v2/bot/message/push"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["payload"] == build_line_push_payload("U123", "ETF summary")
    assert captured["timeout"] == 20


def test_send_line_broadcast_message_posts_without_user_id(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        status = 200

        def __enter__(self) -> "DummyResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request, timeout: int):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    status = send_line_broadcast_message("ETF summary", channel_access_token="token")

    assert status == 200
    assert captured["url"] == "https://api.line.me/v2/bot/message/broadcast"
    assert captured["payload"] == build_line_broadcast_payload("ETF summary")
    assert captured["timeout"] == 20
