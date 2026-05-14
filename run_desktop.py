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
from config import PORT, HOST_DESKTOP


def _start_server() -> None:
    uvicorn.run(app, host=HOST_DESKTOP, port=PORT, log_level="error")


def _wait_for_server(timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST_DESKTOP}:{PORT}/", timeout=1)
            return True
        except Exception:
            time.sleep(0.05)
    return False


def _set_bamf_hint() -> None:
    for p in [
        Path.home() / ".local/share/applications/sysd_ui.desktop",
        Path("/usr/share/applications/sysd_ui.desktop"),
    ]:
        if p.exists():
            os.environ["BAMF_DESKTOP_FILE_HINT"] = str(p)
            return


def _find_browser() -> list[str] | None:
    for name in ("chromium-browser", "chromium", "google-chrome-stable", "google-chrome"):
        if which(name):
            loading = Path(__file__).parent / "web" / "static" / "loading.html"
            profile_dir = Path(__file__).parent / ".chrome-profile"
            cmd = [
                name,
                f"--app=file://{loading}?port={PORT}",
                f"--user-data-dir={profile_dir}",
                "--window-size=1280,800",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--class=sysd_ui",
                "--name=sysd_ui",
            ]
            return cmd
    return None


if __name__ == "__main__":
    _set_bamf_hint()
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    cmd = _find_browser()
    if cmd is None:
        if not _wait_for_server():
            print("Server did not start in time", file=sys.stderr)
            sys.exit(1)
        import webbrowser
        print("No Chromium/Chrome found — opening in default browser")
        webbrowser.open(f"http://{HOST_DESKTOP}:{PORT}/")
        proc = None
    else:
        proc = subprocess.Popen(cmd)
        if not _wait_for_server():
            print("Server did not start in time", file=sys.stderr)

    # Keep server alive until the browser window closes (or Ctrl-C)
    try:
        if cmd:
            proc.wait()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
