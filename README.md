# EverTask — AI Study Planner (MVP)

Study plans that build themselves, live on your calendar.

## What's inside
- `index.html` — the complete app (landing + chat + planner + deskmate + teach mode), single file
- `app.html` — same app (alternate entry point)
- `server.py` — lightweight backend: web search (Wikipedia / Open Library / DuckDuckGo) + NVIDIA NIM proxy (fixes browser CORS)
- `assets/logo.png` — EverTask logo
- `api/` — Vercel serverless functions wrapping the same backend routes (`/api/health`, `/api/models`, `/api/search`, `/api/chat`)
- `vercel.json` — Vercel deployment config (static frontend + Python serverless functions)

## Run it
```bash
cd evertask
python3 server.py
# open http://localhost:8080
```
No dependencies — Python standard library only.

## Deploy to Vercel

The project is Vercel-ready. The stack is split like this:

- **Static frontend** — `index.html`, `app.html`, `assets/logo.png` → served as static files.
- **Serverless API** — `api/health.py`, `api/models.py`, `api/search.py`, `api/chat.py` → Vercel Functions (Python runtime, `BaseHTTPRequestHandler` based), exposed at `/api/health`, `/api/models`, `/api/search`, `/api/chat`.

The frontend calls the API on the **same origin** (`/api/search?q=…`, `/api/chat`), so on Vercel everything just works with no CORS changes and no extra env vars.

### Vercel config (`vercel.json`)
- `buildCommand: ""` → skips the build step; static files are served straight from the project root (framework defaults to "Other" for a plain HTML + Python API project).
- `functions` → one serverless function per API route with its `maxDuration` (Hobby plan allows up to 12 functions per deployment; EverTask uses 4).

### Deploy steps (CLI)
```bash
npm i -g vercel
vercel login
vercel        # preview deployment
vercel --prod # production deployment
```

### Or via GitHub import
1. Push this repo to GitHub (`github.com/agibuilder95-lang`).
2. On Vercel: **Add New → Project → Import Git** → pick the repo.
3. Framework preset should auto-detect as **Other**; build command empty; output directory = project root.
4. Deploy.

## Features
- Chat-first AI planner: real NCERT chapters (Classes 9–12) mapped onto a live calendar
- Artifact panel: watch each day get written, fly up, and slam onto its calendar date
- Interactive plans: tap a date, tick off Learn / Practice / Revise tasks, XP + progress
- Deskmate: pick & name a plushie study buddy that sits with you
- Teach mode (Feynman): teach your deskmate by voice (live transcription) or typing;
  it praises, catches mistakes, and questions you back
- Personal onboarding: name, class, daily hours, goal, plan language (English / Hinglish / Hindi)
- Print / Download (beautiful printable HTML) / Copy for every planner

## Optional: connect NVIDIA NIM AI
1. Get a free key at https://build.nvidia.com (Generate API Key — starts with `nvapi-`)
2. In the app, tap **🔑 API Key** (top bar), paste it, choose a model, tap **Test**
3. The key is stored only in the visitor's browser and sent via the backend proxy.

Without a key, planners, calendar, deskmate and teach-mode (local feedback) still work.

## Notes
- Chats, plans, progress and settings save in the browser's local storage.
- Voice transcription uses the browser's built-in speech recognition (best in Chrome).

## Desktop app (PyInstaller)
Packaged desktop app (self-contained `EverTask.exe`, runs the backend on a local port and hosts the UI in a native window via WebView2):

```bash
pip install pywebview
pyinstaller --onefile --windowed --name EverTask --collect-all webview \
    --add-data "server.py;." --add-data "index.html;." --add-data "app.html;." \
    --add-data "assets;assets" desktop_app.py
```

Output: `dist/EverTask.exe` — no Python install needed on the target machine.
Run with: `EverTask.exe` (or set `EVERTASK_PORT` to change the local port).
