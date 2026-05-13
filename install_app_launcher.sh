#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.local.sysd_ui"
APP_NAME="sysd ui"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${PROJECT_DIR}/run.py"
DESKTOP_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${DESKTOP_DIR}/${APP_ID}.desktop"

if [[ ! -f "${RUNNER}" ]]; then
  echo "run.py not found: ${RUNNER}" >&2
  exit 1
fi

mkdir -p "${DESKTOP_DIR}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Native GTK systemd service manager
Exec=python3 ${RUNNER}
Icon=utilities-system-monitor
Terminal=false
Categories=System;Settings;
StartupNotify=true
StartupWMClass=${APP_ID}
EOF

chmod 0644 "${DESKTOP_FILE}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${DESKTOP_DIR}" >/dev/null 2>&1 || true
fi

echo "Installed launcher: ${DESKTOP_FILE}"
echo "If the app is already running, close and reopen it from the launcher for app-bar grouping."
