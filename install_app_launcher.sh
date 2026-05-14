#!/usr/bin/env bash
set -euo pipefail

APP_ID="sysd_ui"
APP_NAME="sysd ui"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${PROJECT_DIR}/run_desktop.py"
VENV="${PROJECT_DIR}/.venv"

# --system flag installs for all users
if [[ "${1:-}" == "--system" ]]; then
  DESKTOP_DIR="/usr/share/applications"
  SYSTEM_INSTALL=1
else
  DESKTOP_DIR="${HOME}/.local/share/applications"
  SYSTEM_INSTALL=0
fi
DESKTOP_FILE="${DESKTOP_DIR}/${APP_ID}.desktop"

echo "=== sysd_ui installer ==="
echo "Project: ${PROJECT_DIR}"
if [[ "${SYSTEM_INSTALL}" -eq 1 ]]; then
  echo "Mode: system-wide (/usr/share/applications)"
else
  echo "Mode: current user (~/.local/share/applications)"
  echo "Tip: run with --system to install for all users"
fi

# ── system packages ───────────────────────────────────────────────────────────
echo ""
echo "--- Installing system packages ---"

MISSING_PKGS=()

command -v python3 &>/dev/null          || MISSING_PKGS+=("python3")
python3 -m pip --version &>/dev/null    || MISSING_PKGS+=("python3-pip")
python3 -m venv --help &>/dev/null      || MISSING_PKGS+=("python3-venv")
command -v zenity &>/dev/null           || MISSING_PKGS+=("zenity")

if ! command -v chromium-browser &>/dev/null && \
   ! command -v chromium &>/dev/null && \
   ! command -v google-chrome-stable &>/dev/null && \
   ! command -v google-chrome &>/dev/null; then
  MISSING_PKGS+=("chromium-browser")
fi

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  echo "Installing: ${MISSING_PKGS[*]}"
  sudo apt-get update -qq
  sudo apt-get install -y "${MISSING_PKGS[@]}"
else
  echo "All system packages already installed."
fi

# ── python venv + requirements ────────────────────────────────────────────────
echo ""
echo "--- Setting up Python environment ---"

if [[ ! -d "${VENV}" ]]; then
  echo "Creating virtualenv: ${VENV}"
  python3 -m venv "${VENV}"
fi

PYTHON="${VENV}/bin/python3"
PIP="${VENV}/bin/pip"

echo "Installing Python requirements..."
"${PIP}" install --quiet --upgrade pip
"${PIP}" install --quiet -r "${PROJECT_DIR}/requirements.txt"
echo "Python requirements installed."

# ── desktop launcher ──────────────────────────────────────────────────────────
echo ""
echo "--- Installing desktop launcher ---"

if [[ ! -f "${RUNNER}" ]]; then
  echo "run_desktop.py not found: ${RUNNER}" >&2
  exit 1
fi

if [[ "${SYSTEM_INSTALL}" -eq 1 ]]; then
  sudo mkdir -p "${DESKTOP_DIR}"
  WRITE_CMD="sudo tee ${DESKTOP_FILE} > /dev/null"
else
  mkdir -p "${DESKTOP_DIR}"
  WRITE_CMD="tee ${DESKTOP_FILE} > /dev/null"
fi

cat <<EOF | eval "${WRITE_CMD}"
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Web-based systemd service manager
Exec=${PYTHON} ${RUNNER}
Icon=utilities-system-monitor
Terminal=false
Categories=System;Settings;
StartupNotify=true
StartupWMClass=${APP_ID}
EOF

if [[ "${SYSTEM_INSTALL}" -eq 1 ]]; then
  sudo chmod 0644 "${DESKTOP_FILE}"
else
  chmod 0644 "${DESKTOP_FILE}"
fi

if command -v update-desktop-database &>/dev/null; then
  update-desktop-database "${DESKTOP_DIR}" &>/dev/null || true
fi

echo "Launcher installed: ${DESKTOP_FILE}"

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Installation complete ==="
echo "Run from the app launcher or:"
echo "  ${PYTHON} ${RUNNER}"
