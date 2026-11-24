#!/usr/bin/env python3
"""EverTask desktop wrapper.

Hosts the EverTask web app (index.html + /api backend from server.py) inside a
native desktop window (WebView2 on Windows via pywebview) and runs the Python
backend on a local port.

Dev:
    python desktop_app.py

Packaged (PyInstaller):
    pyinstaller --onefile --windowed --name EverTask --collect-all webview \
        --add-data "server.py;." --add-data "index.html;." --add-data "app.html;." \
        --add-data "assets;assets" desktop_app.py

The resulting EverTask.exe is fully self-contained (bundles Python runtime + backend).
Requires the WebView2 runtime (installed automatically on Windows 11 / via Evergreen).
"""
import importlib.util
import os
import sys
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import webview

PORT = int(os.environ.get("EVERTASK_PORT", "8080"))
APP_TITLE = "EverTask — AI Study Planner"


def base_dir() -> str:
    # PyInstaller frozen apps expose the bundled files via sys._MEIPASS
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))


def start_backend():
    """Load server.py from the app directory and serve it on 127.0.0.1:PORT."""
    bdir = base_dir()
    spec = importlib.util.spec_from_file_location(
        "evertask_server", os.path.join(bdir, "server.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), module.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def wait_for_backend(timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{PORT}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def main() -> None:
    httpd = start_backend()
    if not wait_for_backend():
        httpd.shutdown()
        raise RuntimeError("EverTask backend failed to start — check port %s" % PORT)

    window = webview.create_window(
        APP_TITLE,
        url=f"http://127.0.0.1:{PORT}/index.html",
        width=1280,
        height=820,
        resizable=True,
        frameless=False,
        shadow=True,
        focus=True,
    )
    webview.start(private_mode=False)


if __name__ == "__main__":
    main()
