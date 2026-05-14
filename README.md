# sysd_ui

Web-based systemd service manager. Manage, edit, create and monitor systemd units from a browser or a native desktop window.

## Install

```bash
pip install -r requirements.txt
# file picker support (browser mode):
sudo apt install zenity
```

## Run modes

### Browser mode

Starts an HTTP server; open it in any browser.

```bash
python run_web.py                         # http://127.0.0.1:8000
python run_web.py --host 0.0.0.0 --port 8080
```

Protected by login when `.env` credentials are set (see [Auth](#auth)).

### Desktop mode

Wraps the same server in a Chromium `--app` window — no tabs, no address bar.
Requires `chromium-browser` or `google-chrome`. Auth is skipped automatically.

```bash
python run_desktop.py
```

---

## Auth

Create `.env` in the project root (browser mode only — desktop skips auth):

```env
SYSD_UI_USER=admin
SYSD_UI_PASSWORD=yourpassword
```

Without `.env` the app runs unauthenticated.
Add `SYSD_UI_SECRET=<random-hex>` to pin the session signing key across restarts.

---

## Workflows

### View services

The sidebar lists all systemd units grouped by type (Services, Timers, Sockets, …).
Pinned units appear at the top in a **Pinned** section.

- **Search** — filter by name, description, path, status, tags
- **Class filter chips** — All / Custom / App / System / Core
- **★ Favorites** — toggle to show pinned units only
- **Star button** on each row — pin/unpin without opening the unit

### Service actions

Select a unit to open the detail panel. Buttons mirror systemd state:

| State | Buttons |
|---|---|
| active | Stop · Restart |
| failed | Restart · Start |
| inactive | Start |
| any | Enable/Disable · Pin/Unpin · Backup · Restore backup · Mask/Unmask · Delete |

### Tabs

**Info** — runtime metadata: PID, memory, CPU, uptime, load state, dependencies.

**Journal** — last 100 log lines with timestamps.

**Editor** — full unit file editor (see below).

### Editor

Unit file parsed into collapsible `[Section]` blocks.

- **Common fields** (Description, ExecStart, User, …) shown in cyan — always present
- **Other directives** from the file appear in their own section
- **+ Add directive** — append any directive to a section
- **+ Add section** — add a standard systemd section not yet present
- **Browse `…` button** — opens a native file picker (zenity/kdialog) next to path and exec fields
- **Autocomplete** — suggestions on all fields; directive keys filtered to the current section; unit dependency fields validate against running units
- **ExecStart validation** — checks executable exists and is runnable (live, debounced)
- **Path field validation** — checks path exists on disk (live, debounced)
- **Dirty indicator** — `● Modified` / `● Saved` in the footer

**Save modes** (chosen automatically by unit location):

| Unit location | Button label | Behaviour |
|---|---|---|
| `/etc/systemd/system/` | Save unit | Writes file directly |
| `/usr/lib/systemd/system/` | Save vendor unit | Backup first, then overwrite |
| Other | Save override | Writes a drop-in override |

Footer: **Save** · **Backup** · **Restore backup** · **Reload from disk**

### Create a new unit

Click **+ New unit** in the sidebar.

1. Type the unit name — suffix (`.service`, `.timer`, `.socket`, …) determines visible sections
2. Fill in fields; **ExecStart is required**
3. Set **WantedBy** to auto-enable on create
4. Click **Create** — unit is saved, enabled if WantedBy set, pinned, and the editor opens

### Daemon reload

**Daemon reload** button in the header — runs `systemctl daemon-reload` and refreshes the list.

---

## File structure

```
run_web.py          # browser mode entry point
run_desktop.py      # desktop (Chromium app) entry point
.env                # credentials (do not commit)
backend.py          # systemd backend (systemctl, journalctl, unit file I/O)
services.py         # ServiceUnit dataclass
suggestions.py      # directive lists, autocomplete data
web/
  app.py            # FastAPI application, all API routes
  static/
    index.html      # single-page UI
    app.js          # all frontend logic
```
