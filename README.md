# sysd_ui

Native GTK desktop UI concept for managing `systemd` services.

## What is included

- Left-side host and target rail
- Search, status filtering, and sorting for service units
- Service list with state chips and runtime metadata
- Editable unit properties for common directives like `Description`, `ExecStart`, `WorkingDirectory`, `User`, `Group`, `Environment`, and `Restart`
- Property suggestions from systemd directive names and local executable discovery
- Detail panel with actions like start, stop, restart, and journal viewing
- Recent journal and dependency panels
- No embedded browser or webview

## Run

```bash
python3 run.py
```

or:

```bash
python3 main.py
```

## Notes

The current build talks directly to the local `systemctl` and `journalctl` commands from the GTK app, so there is no browser layer. Mutating actions retry through `pkexec` when direct access is denied, which lets polkit handle authorization in the desktop session.
