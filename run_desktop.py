#!/usr/bin/env python3
"""Launch sysd_ui as a desktop app (Chromium/Chrome in app mode)."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import urllib.request

os.environ["SYSD_UI_SKIP_AUTH"] = "1"
from pathlib import Path
from shutil import which

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from web.app import app

PORT = 8766


def _start_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="error")


def _wait_for_server(timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            return True
        except Exception:
            time.sleep(0.05)
    return False


def _find_browser() -> list[str] | None:
    for name in ("chromium-browser", "chromium", "google-chrome-stable", "google-chrome"):
        if which(name):
            return [
                name,
                f"--app=http://127.0.0.1:{PORT}/",
                "--window-size=1280,800",
                "--no-first-run",
                "--no-default-browser-check",
            ]
    return None


if __name__ == "__main__":
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    if not _wait_for_server():
        print("Server did not start in time", file=sys.stderr)
        sys.exit(1)

    cmd = _find_browser()
    if cmd is None:
        import webbrowser
        print(f"No Chromium/Chrome found — opening in default browser")
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    else:
        proc = subprocess.Popen(cmd)

    # Keep server alive until the browser window closes (or Ctrl-C)
    try:
        if cmd:
            proc.wait()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
