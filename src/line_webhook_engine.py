from __future__ import annotations

from pathlib import Path
from typing import Any

from .line_engine import extract_text_messages_from_webhook, parse_self_check_reply
from .pdca_engine import append_self_check_log


def handle_line_webhook_payload(
    payload: dict[str, Any],
    output_path: str | Path = "data/processed/pdca/self_check_log.csv",
) -> dict[str, object]:
    messages = extract_text_messages_from_webhook(payload)
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
        "recorded": recorded,
        "ignored": ignored,
    }
