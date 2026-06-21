from __future__ import annotations

import json

import pytest

from src.line_engine import (
    build_line_broadcast_payload,
    build_line_push_payload,
    check_line_settings,
    extract_text_messages_from_webhook,
    parse_self_check_reply,
    send_line_broadcast_message,
    send_line_push_message,
)
from src.line_webhook_engine import handle_line_webhook_payload


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


def test_parse_self_check_reply_accepts_daily_check_words() -> None:
    assert parse_self_check_reply("守れた") == ("kept", "守れた")
    assert parse_self_check_reply("今日は破った。SOFIを買いそうだった") == ("broke", "今日は破った。SOFIを買いそうだった")
    assert parse_self_check_reply("保留") == ("pending", "保留")
    assert parse_self_check_reply("関係ないメッセージ") is None


def test_extract_text_messages_from_webhook_ignores_non_text_events() -> None:
    payload = {
        "events": [
            {"type": "message", "message": {"type": "text", "text": "守れた"}},
            {"type": "message", "message": {"type": "image", "id": "1"}},
            {"type": "follow"},
        ]
    }

    assert extract_text_messages_from_webhook(payload) == ["守れた"]


def test_handle_line_webhook_payload_records_self_check(tmp_path) -> None:
    output_path = tmp_path / "self_check_log.csv"
    payload = {
        "events": [
            {"type": "message", "message": {"type": "text", "text": "破った SOFIを見て迷った"}},
            {"type": "message", "message": {"type": "text", "text": "雑談"}},
        ]
    }

    result = handle_line_webhook_payload(payload, output_path=output_path)
    text = output_path.read_text(encoding="utf-8")

    assert result == {"messages": 2, "recorded": 1, "ignored": 1}
    assert "破った" in text
    assert "line_webhook" in text


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
