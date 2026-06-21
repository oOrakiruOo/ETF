from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"
LINE_BROADCAST_ENDPOINT = "https://api.line.me/v2/bot/message/broadcast"
SELF_CHECK_REPLY_MAP = {
    "守れた": "kept",
    "まもれた": "kept",
    "守った": "kept",
    "ok": "kept",
    "kept": "kept",
    "破った": "broke",
    "やぶった": "broke",
    "破り": "broke",
    "ng": "broke",
    "broke": "broke",
    "保留": "pending",
    "あとで": "pending",
    "pending": "pending",
}


def check_line_settings() -> dict[str, bool]:
    return {
        "LINE_CHANNEL_ACCESS_TOKEN": bool(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")),
        "LINE_TO_USER_ID": bool(os.environ.get("LINE_TO_USER_ID")),
    }


def build_line_push_payload(to: str, text: str) -> dict[str, Any]:
    return {
        "to": to,
        "messages": [
            {
                "type": "text",
                "text": text,
            }
        ],
    }


def build_line_broadcast_payload(text: str) -> dict[str, Any]:
    return {
        "messages": [
            {
                "type": "text",
                "text": text,
            }
        ],
    }


def parse_self_check_reply(text: str) -> tuple[str, str] | None:
    normalized = text.strip().lower()
    if not normalized:
        return None
    for keyword, status in SELF_CHECK_REPLY_MAP.items():
        if keyword in normalized:
            return status, text.strip()
    return None


def extract_text_messages_from_webhook(payload: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    events = payload.get("events")
    if not isinstance(events, list):
        return messages
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "message":
            continue
        message = event.get("message")
        if not isinstance(message, dict) or message.get("type") != "text":
            continue
        text = message.get("text")
        if isinstance(text, str) and text.strip():
            messages.append(text.strip())
    return messages


def _post_line_payload(payload: dict[str, Any], token: str, endpoint: str) -> int:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LINE送信に失敗しました: HTTP {exc.code} {body}") from exc


def send_line_push_message(
    text: str,
    channel_access_token: str | None = None,
    to_user_id: str | None = None,
    endpoint: str = LINE_PUSH_ENDPOINT,
) -> int:
    token = channel_access_token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    to = to_user_id or os.environ.get("LINE_TO_USER_ID")
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN が未設定です。")
    if not to:
        raise RuntimeError("LINE_TO_USER_ID が未設定です。")

    return _post_line_payload(build_line_push_payload(to, text), token, endpoint)


def send_line_broadcast_message(
    text: str,
    channel_access_token: str | None = None,
    endpoint: str = LINE_BROADCAST_ENDPOINT,
) -> int:
    token = channel_access_token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN が未設定です。")
    return _post_line_payload(build_line_broadcast_payload(text), token, endpoint)
