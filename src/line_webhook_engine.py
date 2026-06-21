from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from .line_engine import extract_text_messages_from_webhook, extract_user_ids_from_webhook, parse_self_check_reply
from .pdca_engine import append_self_check_log
from .utils import PROJECT_ROOT, ensure_dir


DEFAULT_LINE_USER_IDS_PATH = "data/processed/line/line_user_ids.csv"


def verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    if not signature or not channel_secret:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def handle_line_webhook_body(
    body: bytes,
    signature: str = "",
    channel_secret: str | None = None,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    if channel_secret and not verify_line_signature(body, signature, channel_secret):
        return {"ok": False, "error": "invalid_signature", "messages": 0, "recorded": 0, "ignored": 0}
    payload = json.loads(body.decode("utf-8"))
    result = handle_line_webhook_payload(payload, output_path=output_path)
    return {"ok": True, **result}


def handle_line_webhook_payload(
    payload: dict[str, Any],
    output_path: str | Path | None = None,
    user_ids_output_path: str | Path | None = None,
) -> dict[str, object]:
    messages = extract_text_messages_from_webhook(payload)
    user_ids = extract_user_ids_from_webhook(payload)
    if user_ids:
        append_line_user_ids(user_ids, output_path=user_ids_output_path)
    recorded = 0
    ignored = 0
    for message in messages:
        parsed = parse_self_check_reply(message)
        if parsed is None:
            ignored += 1
            continue
        status, reason = parsed
        append_self_check_log(status=status, reason=reason, source="line_webhook", output_path=output_path)
        recorded += 1
    return {
        "messages": len(messages),
        "user_ids": len(user_ids),
        "recorded": recorded,
        "ignored": ignored,
    }


def append_line_user_ids(user_ids: list[str], output_path: str | Path | None = None) -> Path:
    path = Path(output_path) if output_path is not None else PROJECT_ROOT / DEFAULT_LINE_USER_IDS_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    ensure_dir(path.parent)
    existing: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            value = line.strip()
            if value:
                existing.add(value)
    merged = sorted(existing | set(user_ids))
    path.write_text("user_id\n" + "\n".join(merged) + ("\n" if merged else ""), encoding="utf-8")
    return path
