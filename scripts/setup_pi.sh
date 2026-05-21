#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.12.3}"
VENV_DIR="${VENV_DIR:-.venv}"
CLEAN=0
RUN_APT=1

usage() {
  cat <<'EOF'
Usage: ./scripts/setup_pi.sh [--clean] [--no-apt]

Options:
  --clean   Remove the existing .venv before creating a new one.
  --no-apt  Skip apt package installation.

Environment variables:
  PYTHON_VERSION  Python version to install with pyenv. Default: 3.12.3
  VENV_DIR        Virtual environment directory. Default: .venv
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean)
      CLEAN=1
      shift
      ;;
    --no-apt)
      RUN_APT=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "pyproject.toml" || ! -d "reachy_gladiator_lp" ]]; then
  echo "Run this script from the reachy_gladiator_lp project root." >&2
  exit 2
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This setup script is intended for Raspberry Pi OS or another Linux environment." >&2
  exit 2
fi

if [[ "${RUN_APT}" -eq 1 ]]; then
  echo "Installing Raspberry Pi system packages..."
  sudo apt update
  sudo apt install -y git curl make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev llvm libncurses-dev xz-utils \
    tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev v4l-utils
fi

export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
export PATH="${PYENV_ROOT}/bin:${PATH}"

if ! command -v pyenv >/dev/null 2>&1; then
  echo "Installing pyenv..."
  curl https://pyenv.run | bash
fi

if [[ ! -f "${HOME}/.bashrc" ]] || ! grep -q 'PYENV_ROOT' "${HOME}/.bashrc"; then
  cat >> "${HOME}/.bashrc" <<'EOF'

# pyenv setup
export PYENV_ROOT="$HOME/.pyenv"
[[ -d "$PYENV_ROOT/bin" ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
EOF
fi

eval "$(pyenv init - bash)"

echo "Installing Python ${PYTHON_VERSION} with pyenv if needed..."
pyenv install -s "${PYTHON_VERSION}"

if [[ "${CLEAN}" -eq 1 ]]; then
  echo "Removing existing ${VENV_DIR}..."
  rm -rf "${VENV_DIR}"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating ${VENV_DIR} with Python ${PYTHON_VERSION}..."
  "${PYENV_ROOT}/versions/${PYTHON_VERSION}/bin/python" -m venv --copies "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Using Python: $(python --version)"

python -m pip install --upgrade pip setuptools wheel

echo "Installing Pi-compatible MediaPipe and Reachy Mini dependencies..."
python -m pip install "mediapipe==0.10.18"
python -m pip install --upgrade "numpy==2.4.4"
python -m pip install --no-deps --force-reinstall "reachy-mini==1.7.3"

python -m pip install \
  "scipy<2.0.0,>=1.15.3" \
  "reachy_mini_motor_controller>=1.5.5" \
  psutil \
  jinja2 \
  "uvicorn[standard]" \
  fastapi \
  python-multipart \
  "starlette<1.0.0" \
  pyserial \
  "huggingface-hub==1.3.0" \
  "reachy-mini-rust-kinematics>=1.0.3" \
  asgiref \
  aiohttp \
  "log-throttling==0.0.3" \
  "pyusb>=1.2.1" \
  "libusb_package>=1.0.26.3" \
  rich \
  questionary \
  "websockets<16,>=12" \
  toml \
  "rustypot>=1.4.2" \
  pyyaml \
  "requests>=2.28.0" \
  "zeroconf<1,>=0.131" \
  "tornado>=6.5.5" \
  "opencv-python<=5.0"

python -m pip install --no-deps -e .
chmod +x scripts/*.sh

echo
echo "Running import smoke test..."
python - <<'PY'
from importlib.metadata import version
import sys
import numpy
import mediapipe

print("python", sys.version)
print("numpy", numpy.__version__)
print("mediapipe", mediapipe.__version__)
print("reachy-mini", version("reachy-mini"))

import reachy_mini
from reachy_gladiator_lp.main import ReachyGladiatorLp

print("reachy_mini import OK")
print("app import OK:", ReachyGladiatorLp.__name__)
PY

echo
echo "Checking installed packages. A MediaPipe NumPy metadata warning is expected on this Pi setup."
python -m pip check || true

echo
echo "Pi setup complete."
echo "Activate the environment with: source ${VENV_DIR}/bin/activate"
