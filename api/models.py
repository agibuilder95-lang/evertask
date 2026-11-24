import json
from http.server import BaseHTTPRequestHandler

from server import fetch_json

MODEL_EXCLUDE = ("embed", "guard", "safety", "detector", "nvclip", "riva", "ising", "retriever")


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function: GET /api/models"""

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
        try:
            d = fetch_json("https://integrate.api.nvidia.com/v1/models")
            ids = [m.get("id") for m in d.get("data", [])]
            chat = [i for i in ids if i and not any(x in i for x in MODEL_EXCLUDE)]
            self._json(200, {"models": chat})
        except Exception as e:
            self._json(502, {"error": "could not list models", "detail": str(e)})
