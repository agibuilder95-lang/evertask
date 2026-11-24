import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function: GET /api/health"""

    def log_message(self, format, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path == "/api/health":
            self._json(200, {
                "ok": True,
                "time_utc": datetime.now(timezone.utc).isoformat(),
                "time_local": datetime.now().astimezone().isoformat(),
            })
            return
        self._json(404, {"error": "not found"})
