import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from server import FALLBACK_MODELS

NIM_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function: POST /api/chat"""

    def log_message(self, format, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._json(400, {"error": f"bad json: {e}"})
        key = (payload.get("apiKey") or "").strip()
        if not key:
            return self._json(400, {"error": "No NVIDIA NIM API key provided. Paste it in the API bar (nvapi-...)."})
        requested = payload.get("model") or FALLBACK_MODELS[0]
        # Auto model: requested first, then fallbacks — one click, no manual model hunting
        candidates = [requested] + [m for m in FALLBACK_MODELS if m != requested]
        errors = []
        for model in candidates[:4]:
            body = json.dumps({
                "model": model,
                "messages": payload.get("messages") or [],
                "temperature": payload.get("temperature", 0.6),
                "max_tokens": payload.get("max_tokens", 1200),
            }).encode()
            req = urllib.request.Request(NIM_CHAT_URL,
                                         data=body, method="POST",
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer " + key,
                                                  "Accept": "application/json",
                                                  "User-Agent": "EverTask/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = json.loads(r.read().decode())
                    data["_used_model"] = model
                    data["_via"] = "EverTask backend proxy"
                    return self._json(200, data)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "ignore")[:500]
                errors.append(f"{model}: {e.code} {detail[:180]}")
                # 401/403 = key problem, trying other models won't help much but one more may be key-scoped; continue max 2 for auth
                if e.code in (401, 403) and len(errors) >= 2:
                    break
                continue
            except Exception as e:
                errors.append(f"{model}: {e}")
                continue
        return self._json(502, {"error": "NVIDIA NIM failed on all tried models", "detail": " | ".join(errors)})
