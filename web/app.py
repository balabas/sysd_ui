from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend import BackendError, SystemdBackend
from services import ServiceUnit
from suggestions import (
    DIRECTIVE_VALUE_SUGGESTIONS,
    ENVIRONMENT_KEYS,
    SECTION_DIRECTIVE_VALUE_SUGGESTIONS,
    SECTION_DIRECTIVES,
    SYSTEMD_DIRECTIVES,
    command_suggestions,
    disk_suggestions,
    group_suggestions,
    path_suggestions,
    target_suggestions,
    unit_suggestions,
    user_suggestions,
)

# ── credentials from .env ─────────────────────────────────────────────────────

_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH)

_AUTH_USER = os.environ.get("SYSD_UI_USER", "").strip()
_AUTH_PASS = os.environ.get("SYSD_UI_PASSWORD", "").strip()
_AUTH_ENABLED = bool(_AUTH_USER and _AUTH_PASS) and not os.environ.get("SYSD_UI_SKIP_AUTH")

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

_FAVORITES_PATH = Path.home() / ".config" / "sysd_ui" / "favorites.json"


def _load_favorites() -> set[str]:
    try:
        data = json.loads(_FAVORITES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x) for x in data if isinstance(x, str)}
    except Exception:
        pass
    return set()


def _save_favorites(names: set[str]) -> None:
    _FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FAVORITES_PATH.write_text(json.dumps(sorted(names), indent=2), encoding="utf-8")

_SECRET = os.environ.get("SYSD_UI_SECRET", secrets.token_hex(32))


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public = path.startswith("/static/") or path in ("/", "/api/login", "/api/auth-status")
        if not public and _AUTH_ENABLED and not request.session.get("authenticated"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


def _is_authenticated(request: Request) -> bool:
    return not _AUTH_ENABLED or request.session.get("authenticated") is True


app = FastAPI(title="sysd_ui")
app.add_middleware(_AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=_SECRET)
# Allow loading.html (served via file://) to fetch the API in desktop mode
app.add_middleware(CORSMiddleware, allow_origins=["null"], allow_methods=["GET", "POST"])

_backend = SystemdBackend()
_STATIC = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


# ── auth ──────────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(body: LoginBody, request: Request) -> dict:
    if not _AUTH_ENABLED:
        return {"ok": True}
    if _hash(body.username) == _hash(_AUTH_USER) and _hash(body.password) == _hash(_AUTH_PASS):
        request.session["authenticated"] = True
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/api/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth-status")
def auth_status(request: Request) -> dict:
    return {"authenticated": _is_authenticated(request), "enabled": _AUTH_ENABLED}


# ── serialisation ─────────────────────────────────────────────────────────────

def _svc(s: ServiceUnit, favorites: set[str] | None = None) -> dict[str, Any]:
    favs = favorites if favorites is not None else _load_favorites()
    return {
        "name": s.name,
        "description": s.description,
        "status": s.status,
        "enabled": s.enabled,
        "load_state": s.load_state,
        "uptime": s.uptime,
        "since": s.since,
        "pid": s.pid,
        "memory": s.memory,
        "cpu": s.cpu,
        "restarts": s.restarts,
        "path": s.path,
        "target": s.target,
        "tags": s.tags,
        "deps": [{"name": n, "state": st} for n, st in s.deps],
        "service_class": s.service_class,
        "favorite": s.name in favs,
    }


def _raise(exc: BackendError) -> None:
    raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── service list ──────────────────────────────────────────────────────────────

@app.get("/api/services")
def list_services() -> list[dict]:
    favs = _load_favorites()
    return [_svc(s, favs) for s in _backend.list_services()]


# ── sub-resources (must come before the /{name} catch-all) ───────────────────

@app.get("/api/services/{name}/journal")
def get_journal(name: str, lines: int = 100) -> list[dict]:
    return [{"time": t, "message": m} for t, m in _backend.journal(name, lines=lines)]


@app.get("/api/services/{name}/properties")
def get_properties(name: str) -> dict:
    return _backend.read_properties(name)


@app.get("/api/services/{name}/sections")
def get_sections(name: str) -> dict:
    raw = _backend.read_unit_sections(name)
    return {sec: [{"key": k, "value": v} for k, v in pairs]
            for sec, pairs in raw.items()}


# ── single service ────────────────────────────────────────────────────────────

@app.get("/api/services/{name}")
def get_service(name: str) -> dict:
    svc = next((s for s in _backend.list_services() if s.name == name), None)
    if svc is None:
        raise HTTPException(404, f"not found: {name}")
    return _svc(svc)


# ── actions ───────────────────────────────────────────────────────────────────

def _do(fn, *args) -> dict:
    try:
        fn(*args)
        return {"ok": True}
    except BackendError as exc:
        _raise(exc)


@app.post("/api/services/{name}/start")
def start(name: str) -> dict:    return _do(_backend.start, name)

@app.post("/api/services/{name}/stop")
def stop(name: str) -> dict:     return _do(_backend.stop, name)

@app.post("/api/services/{name}/restart")
def restart(name: str) -> dict:  return _do(_backend.restart, name)

@app.post("/api/services/{name}/enable")
def enable(name: str) -> dict:   return _do(_backend.enable, name)

@app.post("/api/services/{name}/disable")
def disable(name: str) -> dict:  return _do(_backend.disable, name)

@app.post("/api/services/{name}/mask")
def mask(name: str) -> dict:     return _do(_backend.mask, name)

@app.post("/api/services/{name}/unmask")
def unmask(name: str) -> dict:   return _do(_backend.unmask, name)


# ── suggestions ──────────────────────────────────────────────────────────────

@app.get("/api/suggestions/static")
def suggestions_static() -> dict:
    return {
        "directives": SYSTEMD_DIRECTIVES,
        "section_directives": {sec: list(dirs) for sec, dirs in SECTION_DIRECTIVES.items()},
        "values": DIRECTIVE_VALUE_SUGGESTIONS,
        "section_values": {
            sec: dict(vals)
            for sec, vals in SECTION_DIRECTIVE_VALUE_SUGGESTIONS.items()
        },
        "env_keys": ENVIRONMENT_KEYS,
    }


@app.get("/api/suggestions/dynamic")
def suggestions_dynamic() -> dict:
    return {
        "users":    user_suggestions(),
        "groups":   group_suggestions(),
        "targets":  target_suggestions(),
        "units":    unit_suggestions(),
        "commands": command_suggestions()[:300],
        "disks":    disk_suggestions(),
    }


@app.get("/api/suggestions/paths")
def suggestions_paths(prefix: str = "") -> list[str]:
    return path_suggestions(prefix)


@app.get("/api/pick-file")
def pick_file(directory: bool = False) -> dict:
    import subprocess
    env = os.environ.copy()
    # ensure dialog appears on the current display
    env.setdefault("DISPLAY", ":0")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""))

    zenity_cmd = ["zenity", "--file-selection", "--title=Select file"] + (["--directory"] if directory else [])
    kdialog_cmd = ["kdialog", "--title", "Select file",
                   "--getexistingdirectory" if directory else "--getopenfilename", "."]

    for cmd in (zenity_cmd, kdialog_cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            path = r.stdout.strip()
            if r.returncode == 0 and path:
                return {"ok": True, "path": path}
            if r.returncode == 0:
                return {"ok": False, "path": "", "message": "cancelled"}
            # non-zero = user cancelled
            return {"ok": False, "path": "", "message": "cancelled"}
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return {"ok": False, "path": "", "message": "Dialog timed out"}
        except Exception as exc:
            return {"ok": False, "path": "", "message": str(exc)}

    return {"ok": False, "path": "", "message": "No file dialog found — install zenity: sudo apt install zenity"}


@app.get("/api/check-path")
def check_path(path: str) -> dict:
    import os
    from pathlib import Path
    p = Path(path.strip()).expanduser()
    if not p.exists():
        return {"exists": False, "is_dir": False, "message": f"Path does not exist: {p}"}
    if p.is_dir():
        return {"exists": True, "is_dir": True, "message": f"Directory: {p}"}
    return {"exists": True, "is_dir": False, "message": f"File exists: {p}"}


@app.get("/api/check-exec")
def check_exec(cmd: str) -> dict:
    import shlex, os
    from pathlib import Path
    from shutil import which
    cmd = cmd.strip()
    if not cmd:
        return {"ok": False, "message": "ExecStart is required"}
    try:
        token = shlex.split(cmd, posix=True)[0]
    except ValueError:
        token = cmd.split()[0] if cmd.split() else cmd
    token = token.lstrip("@-+!")
    if not token:
        return {"ok": False, "message": "ExecStart is required"}
    if token.startswith(("/", ".", "~")):
        p = Path(token).expanduser()
        if not p.exists():
            return {"ok": False, "message": f"Path does not exist: {p}"}
        if p.is_dir():
            return {"ok": False, "message": f"Points to a directory: {p}"}
        if not os.access(p, os.X_OK):
            return {"ok": False, "message": f"Not executable: {p}"}
        return {"ok": True, "message": ""}
    resolved = which(token)
    if resolved is None:
        return {"ok": False, "message": f"Command not found in PATH: {token}"}
    return {"ok": True, "message": ""}


# ── daemon reload ─────────────────────────────────────────────────────────────

@app.post("/api/daemon-reload")
def daemon_reload() -> dict:
    try:
        _backend.daemon_reload()
        return {"ok": True}
    except BackendError as exc:
        _raise(exc)


# ── save override ─────────────────────────────────────────────────────────────

class SaveBody(BaseModel):
    fields: dict[str, str]
    extra: list[list[str]]  # [[key, value], …]


@app.post("/api/services/{name}/save")
def save_override(name: str, body: SaveBody) -> dict:
    extra = [(r[0], r[1]) for r in body.extra if len(r) == 2]
    try:
        _backend.save_override(name, body.fields, extra)
        return {"ok": True}
    except BackendError as exc:
        _raise(exc)


# ── create ────────────────────────────────────────────────────────────────────

class CreateBody(BaseModel):
    name: str
    fields: dict[str, str]
    extra: list[list[str]]


@app.post("/api/services")
def create(body: CreateBody) -> dict:
    extra = [(r[0], r[1]) for r in body.extra if len(r) == 2]
    try:
        unit_name = _backend.create_service(body.name, body.fields, extra)
        return {"ok": True, "name": unit_name}
    except BackendError as exc:
        _raise(exc)


# ── required-by ───────────────────────────────────────────────────────────────

@app.get("/api/services/{name}/required-by")
def required_by(name: str) -> dict:
    return {"units": _backend.required_by(name)}


# ── backup / restore ──────────────────────────────────────────────────────────

@app.post("/api/services/{name}/backup")
def backup(name: str) -> dict:
    svc = next((s for s in _backend.list_services() if s.name == name), None)
    path = (svc.path or "").strip() if svc else ""
    if not path:
        raise HTTPException(400, f"unit file path is unknown for {name}")
    try:
        backup_path = _backend.backup_unit_file(name, path)
        return {"ok": True, "backup": backup_path}
    except BackendError as exc:
        _raise(exc)


@app.post("/api/services/{name}/restore-backup")
def restore_backup(name: str) -> dict:
    svc = next((s for s in _backend.list_services() if s.name == name), None)
    path = (svc.path or "").strip() if svc else ""
    if not path:
        raise HTTPException(400, f"unit file path is unknown for {name}")
    try:
        backup_path = _backend.restore_unit_backup(name, path)
        return {"ok": True, "backup": backup_path}
    except BackendError as exc:
        _raise(exc)


# ── save unit (for custom/app units in /etc/systemd/system/) ─────────────────

@app.post("/api/services/{name}/save-unit")
def save_unit(name: str, body: SaveBody) -> dict:
    extra = [(r[0], r[1]) for r in body.extra if len(r) == 2]
    try:
        _backend.save_unit(name, body.fields, extra)
        return {"ok": True}
    except BackendError as exc:
        _raise(exc)


@app.post("/api/services/{name}/save-vendor-unit")
def save_vendor_unit(name: str, body: SaveBody) -> dict:
    extra = [(r[0], r[1]) for r in body.extra if len(r) == 2]
    svc = next((s for s in _backend.list_services() if s.name == name), None)
    path = (svc.path or "").strip() if svc else ""
    if not path:
        raise HTTPException(400, f"unit file path is unknown for {name}")
    try:
        _backend.save_vendor_unit(name, path, body.fields, extra)
        return {"ok": True}
    except BackendError as exc:
        _raise(exc)


# ── favorites ─────────────────────────────────────────────────────────────────

@app.post("/api/services/{name}/favorite")
def toggle_favorite(name: str) -> dict:
    favs = _load_favorites()
    if name in favs:
        favs.discard(name)
        is_fav = False
    else:
        favs.add(name)
        is_fav = True
    _save_favorites(favs)
    return {"ok": True, "favorite": is_fav}


# ── delete ────────────────────────────────────────────────────────────────────

@app.delete("/api/services/{name}")
def delete(name: str) -> dict:
    try:
        _backend.delete_service(name)
        return {"ok": True}
    except BackendError as exc:
        _raise(exc)
