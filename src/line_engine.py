from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


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

    payload = json.dumps(build_line_push_payload(to, text), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
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
