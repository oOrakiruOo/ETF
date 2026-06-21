from __future__ import annotations

import json
import base64
import hashlib
import hmac

import pytest

from src.line_engine import (
    append_line_delivery_log,
    build_line_broadcast_payload,
    build_line_push_payload,
    check_line_settings,
    extract_text_messages_from_webhook,
    extract_user_ids_from_webhook,
    parse_self_check_reply,
    send_line_broadcast_message,
    send_line_push_message,
)
from src.line_webhook_engine import handle_line_webhook_body, handle_line_webhook_payload, verify_line_signature


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


def test_append_line_delivery_log_writes_non_secret_delivery_record(tmp_path) -> None:
    output_path = append_line_delivery_log(
        mode="broadcast",
        command="line-broadcast-decision-brief",
        source_path="reports/daily/decision_brief_2026-06-21.txt",
        http_status=200,
        output_dir=tmp_path,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "line-broadcast-decision-brief" in text
    assert "reports/daily/decision_brief_2026-06-21.txt" in text
    assert "200" in text
    assert "LINE_CHANNEL_ACCESS_TOKEN" not in text


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


def test_extract_user_ids_from_webhook_returns_unique_line_user_ids() -> None:
    payload = {
        "events": [
            {"source": {"type": "user", "userId": "U111"}},
            {"source": {"type": "user", "userId": "U111"}},
            {"source": {"type": "group", "groupId": "G222"}},
            {"source": {"type": "user", "userId": "invalid"}},
            {"type": "follow", "source": {"type": "user", "userId": "U333"}},
        ]
    }

    assert extract_user_ids_from_webhook(payload) == ["U111", "U333"]


def test_handle_line_webhook_payload_records_self_check(tmp_path) -> None:
    output_path = tmp_path / "self_check_log.csv"
    user_ids_output_path = tmp_path / "line_user_ids.csv"
    payload = {
        "events": [
            {
                "type": "message",
                "source": {"type": "user", "userId": "U123"},
                "message": {"type": "text", "text": "破った SOFIを見て迷った"},
            },
            {"type": "message", "message": {"type": "text", "text": "雑談"}},
        ]
    }

    result = handle_line_webhook_payload(payload, output_path=output_path, user_ids_output_path=user_ids_output_path)
    text = output_path.read_text(encoding="utf-8")

    assert result == {"messages": 2, "user_ids": 1, "recorded": 1, "ignored": 1}
    assert "破った" in text
    assert "line_webhook" in text
    assert "U123" in user_ids_output_path.read_text(encoding="utf-8")


def test_handle_line_webhook_body_verifies_signature_and_records(tmp_path) -> None:
    output_path = tmp_path / "self_check_log.csv"
    body = json.dumps({"events": [{"type": "message", "message": {"type": "text", "text": "守れた"}}]}).encode("utf-8")
    secret = "channel-secret"
    signature = base64.b64encode(hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()).decode("utf-8")

    assert verify_line_signature(body, signature, secret)
    result = handle_line_webhook_body(body, signature=signature, channel_secret=secret, output_path=output_path)

    assert result == {"ok": True, "messages": 1, "user_ids": 0, "recorded": 1, "ignored": 0}
    assert "守れた" in output_path.read_text(encoding="utf-8")


def test_handle_line_webhook_body_rejects_invalid_signature(tmp_path) -> None:
    body = b'{"events":[]}'
    result = handle_line_webhook_body(
        body,
        signature="invalid",
        channel_secret="channel-secret",
        output_path=tmp_path / "self_check_log.csv",
    )

    assert result["ok"] is False
    assert result["error"] == "invalid_signature"


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
