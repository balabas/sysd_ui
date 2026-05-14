#!/usr/bin/env bash
set -euo pipefail

APP_ID="sysd_ui"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${PROJECT_DIR}/.venv"

REMOVE_VENV=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge) REMOVE_VENV=1; shift ;;
    *) echo "Unknown option: $1" >&2; echo "Usage: $0 [--purge]" >&2; exit 1 ;;
  esac
done

echo "=== sysd_ui uninstaller ==="
echo ""

# ── systemd service ───────────────────────────────────────────────────────────
SERVICE_FILE="/etc/systemd/system/${APP_ID}.service"
if [[ -f "${SERVICE_FILE}" ]]; then
  echo "--- Removing systemd service ---"
  sudo systemctl stop    "${APP_ID}.service" 2>/dev/null && echo "Stopped service."   || true
  sudo systemctl disable "${APP_ID}.service" 2>/dev/null && echo "Disabled service." || true
  sudo rm -f "${SERVICE_FILE}"
  sudo systemctl daemon-reload
  echo "Service removed."
else
  echo "No systemd service found (${SERVICE_FILE})."
fi

# ── desktop launchers ─────────────────────────────────────────────────────────
echo ""
echo "--- Removing desktop launchers ---"
REMOVED_DESKTOP=0
for dir in "${HOME}/.local/share/applications" "/usr/share/applications"; do
  for id in "${APP_ID}" "com.local.${APP_ID}"; do
    f="${dir}/${id}.desktop"
    if [[ -f "${f}" ]]; then
      if [[ "${dir}" == /usr/* ]]; then
        sudo rm -f "${f}" && echo "Removed (system): ${f}"
      else
        rm -f "${f}" && echo "Removed (user): ${f}"
      fi
      REMOVED_DESKTOP=1
    fi
  done
done
[[ "${REMOVED_DESKTOP}" -eq 0 ]] && echo "No desktop launchers found."

# Update desktop database if available
for dir in "${HOME}/.local/share/applications" "/usr/share/applications"; do
  command -v update-desktop-database &>/dev/null && \
    update-desktop-database "${dir}" &>/dev/null || true
done

# ── chrome profile ────────────────────────────────────────────────────────────
CHROME_PROFILE="${PROJECT_DIR}/.chrome-profile"
if [[ -d "${CHROME_PROFILE}" ]]; then
  echo ""
  echo "--- Removing Chromium profile ---"
  rm -rf "${CHROME_PROFILE}"
  echo "Removed: ${CHROME_PROFILE}"
fi

# ── venv (only with --purge) ──────────────────────────────────────────────────
if [[ "${REMOVE_VENV}" -eq 1 ]]; then
  echo ""
  echo "--- Removing Python virtualenv ---"
  if [[ -d "${VENV}" ]]; then
    rm -rf "${VENV}"
    echo "Removed: ${VENV}"
  else
    echo "No virtualenv found."
  fi
else
  echo ""
  echo "Tip: run with --purge to also remove the Python virtualenv."
fi

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Uninstall complete ==="
