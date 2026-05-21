#!/usr/bin/env bash
set -euo pipefail

HOST="${REACHY_SIM_HOST:-0.0.0.0}"
PORT="${REACHY_SIM_PORT:-8000}"
HEADLESS="${REACHY_SIM_HEADLESS:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT_NAME="$(basename "$0")"
SOCKET_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [[ ! -x "${SOCKET_PYTHON}" ]]; then
  if command -v python >/dev/null 2>&1; then
    SOCKET_PYTHON="python"
  else
    SOCKET_PYTHON="python3"
  fi
fi

is_port_busy() {
  "${SOCKET_PYTHON}" - "$PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    busy = sock.connect_ex(("127.0.0.1", port)) == 0
sys.exit(0 if busy else 1)
PY
}

if is_port_busy; then
  echo "Port ${PORT} is already in use."
  echo
  echo "Either stop the process currently using it, or start the sim on another port:"
  echo "  REACHY_SIM_PORT=18000 ./scripts/${SCRIPT_NAME}"
  echo
  echo "Then point the Pi app at the same port:"
  echo "  REACHY_GLADIATOR_DAEMON_PORT=18000"
  exit 2
fi

if [[ -n "${REACHY_SIM_PYTHON:-}" ]]; then
  PYTHON_BIN="${REACHY_SIM_PYTHON}"
elif [[ "$(uname -s)" == "Darwin" && -x "${PROJECT_ROOT}/.venv/bin/mjpython" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/mjpython"
elif [[ "$(uname -s)" == "Darwin" ]] && command -v mjpython >/dev/null 2>&1; then
  PYTHON_BIN="mjpython"
elif [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  PYTHON_BIN="python3"
fi

if [[ "$(uname -s)" == "Darwin" && "${PYTHON_BIN}" == *mjpython* && -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_LIBDIR="$("${PROJECT_ROOT}/.venv/bin/python" <<'PY'
import os
import sysconfig

libdir = sysconfig.get_config_var("LIBDIR")
ldlibrary = sysconfig.get_config_var("LDLIBRARY")
if libdir and ldlibrary and os.path.exists(os.path.join(libdir, ldlibrary)):
    print(libdir)
PY
)"
  if [[ -n "${PYTHON_LIBDIR}" ]]; then
    export DYLD_LIBRARY_PATH="${PYTHON_LIBDIR}${DYLD_LIBRARY_PATH:+:${DYLD_LIBRARY_PATH}}"
    export DYLD_FALLBACK_LIBRARY_PATH="${PYTHON_LIBDIR}${DYLD_FALLBACK_LIBRARY_PATH:+:${DYLD_FALLBACK_LIBRARY_PATH}}"
  fi
fi

ARGS=(
  -m reachy_mini.daemon.app.main
  --sim
  --fastapi-host "${HOST}"
  --fastapi-port "${PORT}"
  --no-localhost-only
)

if [[ "${HEADLESS}" == "1" || "${HEADLESS}" == "true" ]]; then
  ARGS+=(--headless)
fi

echo "Starting Reachy Mini MuJoCo simulation on ${HOST}:${PORT}"
echo "Runtime: ${PYTHON_BIN}"
echo "Headless: ${HEADLESS}"
echo
echo "Use the host machine IP as REACHY_GLADIATOR_DAEMON_HOST on the Pi."

exec "${PYTHON_BIN}" "${ARGS[@]}"
