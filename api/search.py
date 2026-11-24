import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from server import web_search


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function: GET /api/search?q=..."""

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
        parsed = urlparse(self.path)
        q = (parse_qs(parsed.query).get("q") or [""])[0].strip()
        if not q:
            return self._json(400, {"error": "missing q"})
        results = web_search(q)
        self._json(200, {"query": q, "results": results, "fetched_at": datetime.now().astimezone().isoformat()})
