#!/usr/bin/env python3
"""EverTask backend: static files + NVIDIA NIM proxy (fixes CORS 'Failed to fetch') + web search."""
import json, os, urllib.request, urllib.parse, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
FALLBACK_MODELS = ["nvidia/nemotron-3-ultra-550b-a55b","google/gemma-3-12b-it","google/gemma-4-31b-it","z-ai/glm-5.3-flash","minimaxai/minimax-m3.1-flash","moonshotai/kimi-k3.1-pro"]

def fetch_json(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "EverTask/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))

def web_search(q, limit=6):
    out = []
    # Wikipedia (CORS-friendly, reliable, real-time)
    try:
        u = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": limit})
        d = fetch_json(u)
        for it in d.get("query", {}).get("search", []):
            title = it["title"]
            out.append({"source": "Wikipedia", "title": title,
                        "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                        "snippet": it.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")[:300]})
    except Exception as e:
        out.append({"source": "Wikipedia", "title": "search error", "url": "", "snippet": str(e)[:120]})
    # Open Library - real books
    try:
        u = "https://openlibrary.org/search.json?" + urllib.parse.urlencode({"q": q, "limit": 4})
        d = fetch_json(u)
        for b in d.get("docs", []):
            out.append({"source": "Open Library", "title": b.get("title", ""),
                        "url": "https://openlibrary.org" + (b.get("key", "") or ""),
                        "snippet": ("by " + ", ".join(b.get("author_name", [])[:2]) +
                                    (f" • {b.get('first_publish_year')}" if b.get("first_publish_year") else "") +
                                    (f" • Publisher: {b['publisher'][0]}" if b.get("publisher") else ""))})
    except Exception:
        pass
    # DuckDuckGo Instant Answers
    try:
        u = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({"q": q, "format": "json", "no_html": 1, "skip_disambig": 1})
        d = fetch_json(u)
        if d.get("AbstractText"):
            out.insert(0, {"source": "DuckDuckGo", "title": d.get("Heading") or q,
                           "url": d.get("AbstractURL", ""), "snippet": d["AbstractText"][:400]})
        for t in (d.get("RelatedTopics") or [])[:4]:
            if t.get("Text"):
                out.append({"source": "DuckDuckGo", "title": t["Text"][:90], "url": t.get("FirstURL", ""), "snippet": t["Text"][:300]})
    except Exception:
        pass
    return out

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)
    def log_message(self, *a):
        pass
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        super().end_headers()
    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json(200, {"ok": True, "time_utc": datetime.now(timezone.utc).isoformat(),
                                        "time_local": datetime.now().astimezone().isoformat()})
        if parsed.path == "/api/models":
            try:
                d = fetch_json("https://integrate.api.nvidia.com/v1/models")
                ids = [m.get("id") for m in d.get("data", [])]
                chat = [i for i in ids if i and not any(x in i for x in ("embed","guard","safety","detector","nvclip","riva","ising","retriever"))]
                return self.send_json(200, {"models": chat})
            except Exception as e:
                return self.send_json(502, {"error": "could not list models", "detail": str(e)})
        if parsed.path == "/api/search":
            q = (urllib.parse.parse_qs(parsed.query).get("q") or [""])[0].strip()
            if not q:
                return self.send_json(400, {"error": "missing q"})
            return self.send_json(200, {"query": q, "results": web_search(q),
                                        "fetched_at": datetime.now().astimezone().isoformat()})
        return super().do_GET()
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/models":
            return self.do_GET()
        if parsed.path != "/api/chat":
            return self.send_json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self.send_json(400, {"error": f"bad json: {e}"})
        key = (payload.get("apiKey") or "").strip()
        if not key:
            return self.send_json(400, {"error": "No NVIDIA NIM API key provided. Paste it in the API bar (nvapi-...)."})
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
            req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",
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
                    return self.send_json(200, data)
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
        return self.send_json(502, {"error": "NVIDIA NIM failed on all tried models", "detail": " | ".join(errors)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"EverTask on 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
