from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.line_webhook_engine import handle_line_webhook_body  # noqa: E402


class LineWebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        self._send_json(200, {"ok": True})

    def do_POST(self) -> None:
        if self.path != "/line-webhook":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(content_length)
        result = handle_line_webhook_body(
            body,
            signature=self.headers.get("X-Line-Signature", ""),
            channel_secret=os.environ.get("LINE_CHANNEL_SECRET"),
        )
        status = 200 if result.get("ok") else 403
        self._send_json(status, result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), LineWebhookHandler)
    print(f"LINE webhook server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
