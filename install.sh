#!/usr/bin/env bash
set -euo pipefail

APP_ID="sysd_ui"
APP_NAME="sysd ui"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${PROJECT_DIR}/.venv"
PYTHON="${VENV}/bin/python3"
PIP="${VENV}/bin/pip"

echo "=== sysd_ui installer ==="
echo "Project: ${PROJECT_DIR}"
echo ""

# ── choose install mode ───────────────────────────────────────────────────────
echo "Install mode:"
echo "  [1] Desktop app  — Chromium window + app launcher (local use)"
echo "  [2] Server       — Web server accessible over the network"
echo ""
read -rp "Choice [1]: " _mode
case "${_mode}" in
  2) MODE="server" ;;
  *) MODE="desktop" ;;
esac
echo ""

# ── read port default from config.py ─────────────────────────────────────────
CFG_PORT=$(python3 -c "import sys; sys.path.insert(0,'${PROJECT_DIR}'); from config import PORT; print(PORT)" 2>/dev/null || echo "8766")

# ── server: ask config upfront ────────────────────────────────────────────────
if [[ "${MODE}" == "server" ]]; then
  DEFAULT_HOST="${SYSD_UI_HOST:-0.0.0.0}"
  DEFAULT_PORT="${SYSD_UI_PORT:-${CFG_PORT}}"
  DEFAULT_USER="${SYSD_UI_USER:-$(logname 2>/dev/null || whoami)}"

  read -rp "Bind host   [${DEFAULT_HOST}]: " _h; HOST="${_h:-${DEFAULT_HOST}}"
  read -rp "Port        [${DEFAULT_PORT}]: " _p; PORT="${_p:-${DEFAULT_PORT}}"
  read -rp "Run as user [${DEFAULT_USER}]: " _u; RUN_USER="${_u:-${DEFAULT_USER}}"
  echo ""

  # read current credentials from .env as defaults
  ENV_FILE="${PROJECT_DIR}/.env"
  CURRENT_LOGIN=$(grep -oP '(?<=SYSD_UI_USER=)\S+' "${ENV_FILE}" 2>/dev/null || echo "admin")

  read -rp  "Login username [${CURRENT_LOGIN}]: " _login
  AUTH_USER="${_login:-${CURRENT_LOGIN}}"
  while true; do
    read -rsp "Login password: " AUTH_PASS; echo ""
    read -rsp "Confirm password: " AUTH_PASS2; echo ""
    [[ "${AUTH_PASS}" == "${AUTH_PASS2}" ]] && break
    echo "Passwords do not match, try again."
  done
  echo ""

  read -rp "Install as systemd service (auto-start on boot)? [Y/n]: " _s
  case "${_s,,}" in
    n|no) AS_SERVICE="no" ;;
    *)    AS_SERVICE="yes" ;;
  esac
  echo ""
  echo "--- Summary ---"
  echo "  Mode    : server"
  echo "  Listen  : ${HOST}:${PORT}"
  echo "  Run as  : ${RUN_USER}"
  echo "  Login   : ${AUTH_USER}"
  echo "  Service : ${AS_SERVICE}"
else
  # desktop: check --system flag for scope
  DESKTOP_DIR="${HOME}/.local/share/applications"
  SYSTEM_INSTALL=0
  if [[ "${1:-}" == "--system" ]]; then
    DESKTOP_DIR="/usr/share/applications"
    SYSTEM_INSTALL=1
  fi
  echo "--- Summary ---"
  echo "  Mode    : desktop"
  if [[ "${SYSTEM_INSTALL}" -eq 1 ]]; then
    echo "  Scope   : system-wide (/usr/share/applications)"
  else
    echo "  Scope   : current user (~/.local/share/applications)"
  fi
fi

echo ""
read -rp "Proceed? [Y/n]: " _confirm
case "${_confirm,,}" in
  n|no) echo "Aborted."; exit 0 ;;
esac
echo ""

# ── update config.py if port changed ─────────────────────────────────────────
if [[ "${MODE}" == "server" && "${PORT}" != "${CFG_PORT}" ]]; then
  sed -i "s/^PORT = .*/PORT = ${PORT}/" "${PROJECT_DIR}/config.py"
  echo "config.py updated: PORT = ${PORT}"
  echo ""
fi

# ── write .env with credentials ──────────────────────────────────────────────
if [[ "${MODE}" == "server" ]]; then
  ENV_FILE="${PROJECT_DIR}/.env"
  printf 'SYSD_UI_USER=%s\nSYSD_UI_PASSWORD=%s\n' "${AUTH_USER}" "${AUTH_PASS}" > "${ENV_FILE}"
  chmod 0600 "${ENV_FILE}"
  echo ".env updated with credentials."
  echo ""
fi

# ── detect + stop existing service ────────────────────────────────────────────
SERVICE_FILE="/etc/systemd/system/${APP_ID}.service"
if [[ -f "${SERVICE_FILE}" ]]; then
  echo "Existing service installation detected."
  if systemctl is-active --quiet "${APP_ID}.service" 2>/dev/null; then
    echo "Stopping running service..."
    sudo systemctl stop "${APP_ID}.service"
  fi
  echo ""
fi

# ── system packages ───────────────────────────────────────────────────────────
echo "--- Installing system packages ---"

MISSING_PKGS=()
command -v python3 &>/dev/null       || MISSING_PKGS+=("python3")
python3 -m pip --version &>/dev/null || MISSING_PKGS+=("python3-pip")
python3 -m venv --help &>/dev/null   || MISSING_PKGS+=("python3-venv")

if [[ "${MODE}" == "desktop" ]]; then
  command -v zenity &>/dev/null || MISSING_PKGS+=("zenity")
  if ! command -v chromium-browser &>/dev/null && \
     ! command -v chromium &>/dev/null && \
     ! command -v google-chrome-stable &>/dev/null && \
     ! command -v google-chrome &>/dev/null; then
    MISSING_PKGS+=("chromium-browser")
  fi
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

echo "Installing Python requirements..."
"${PIP}" install --quiet --upgrade pip
"${PIP}" install --quiet -r "${PROJECT_DIR}/requirements.txt"
echo "Python requirements installed."

# ── desktop mode: launcher ────────────────────────────────────────────────────
if [[ "${MODE}" == "desktop" ]]; then
  echo ""
  echo "--- Installing desktop launcher ---"

  RUNNER="${PROJECT_DIR}/run_desktop.py"
  DESKTOP_FILE="${DESKTOP_DIR}/${APP_ID}.desktop"

  # Remove old entries
  for old in com.local.sysd_ui; do
    for dir in "${HOME}/.local/share/applications" "/usr/share/applications"; do
      [[ -f "${dir}/${old}.desktop" ]] && rm -f "${dir}/${old}.desktop" && echo "Removed old entry: ${old}.desktop"
    done
  done

  if [[ ! -f "${RUNNER}" ]]; then
    echo "run_desktop.py not found: ${RUNNER}" >&2; exit 1
  fi

  DESKTOP_CONTENT="[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Web-based systemd service manager
Exec=${PYTHON} ${RUNNER}
Path=${PROJECT_DIR}
Icon=utilities-system-monitor
Terminal=false
Categories=System;Settings;
StartupNotify=false
StartupWMClass=${APP_ID}"

  if [[ "${SYSTEM_INSTALL}" -eq 1 ]]; then
    sudo mkdir -p "${DESKTOP_DIR}"
    echo "${DESKTOP_CONTENT}" | sudo tee "${DESKTOP_FILE}" > /dev/null
    sudo chmod 0644 "${DESKTOP_FILE}"
  else
    mkdir -p "${DESKTOP_DIR}"
    echo "${DESKTOP_CONTENT}" > "${DESKTOP_FILE}"
    chmod 0644 "${DESKTOP_FILE}"
  fi

  command -v update-desktop-database &>/dev/null && \
    update-desktop-database "${DESKTOP_DIR}" &>/dev/null || true

  echo "Launcher installed: ${DESKTOP_FILE}"
fi

# ── server mode: systemd service ──────────────────────────────────────────────
if [[ "${MODE}" == "server" ]]; then
  echo ""
  if [[ "${AS_SERVICE}" == "yes" ]]; then
    echo "--- Installing systemd service ---"

    sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=sysd_ui — web-based systemd service manager
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON} ${PROJECT_DIR}/run_web.py --host ${HOST} --port ${PORT}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    sudo chmod 0644 "${SERVICE_FILE}"
    sudo systemctl daemon-reload
    sudo systemctl enable "${APP_ID}.service"
    sudo systemctl start  "${APP_ID}.service"
    echo "Service installed, enabled, and started."
  else
    # Clean up stale service file if switching to manual
    if [[ -f "${SERVICE_FILE}" ]]; then
      sudo systemctl disable "${APP_ID}.service" 2>/dev/null || true
      sudo rm -f "${SERVICE_FILE}"
      sudo systemctl daemon-reload
      echo "Existing service removed (manual launch mode)."
    fi
  fi
fi

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Installation complete ==="
echo ""

if [[ "${MODE}" == "desktop" ]]; then
  echo "Launch from the app menu or:"
  echo "  ${PYTHON} ${PROJECT_DIR}/run_desktop.py"
else
  echo "Access the UI at:  http://${HOST}:${PORT}"
  echo ""
  if [[ "${AS_SERVICE}" == "yes" ]]; then
    echo "Service commands:"
    echo "  sudo systemctl status  ${APP_ID}"
    echo "  sudo systemctl stop    ${APP_ID}"
    echo "  sudo systemctl restart ${APP_ID}"
    echo "  sudo journalctl -u ${APP_ID} -f"
  else
    echo "Start manually:"
    echo "  ${PYTHON} ${PROJECT_DIR}/run_web.py --host ${HOST} --port ${PORT}"
  fi
fi

echo ""
echo "To uninstall: bash ${PROJECT_DIR}/uninstall.sh"
