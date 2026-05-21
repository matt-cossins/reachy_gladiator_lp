#!/usr/bin/env bash
set -euo pipefail

echo "Video devices:"
ls /dev/video* 2>/dev/null || true

if command -v v4l2-ctl >/dev/null 2>&1; then
  echo
  v4l2-ctl --list-devices || true
fi

python - <<'PY'
import os
import sys

index = int(os.environ.get("REACHY_GLADIATOR_CAMERA_INDEX", "0"))
try:
    import cv2
except Exception as exc:
    print(f"OpenCV import failed: {exc}")
    sys.exit(1)

capture = cv2.VideoCapture(index)
if not capture.isOpened():
    print(f"Could not open USB camera index {index}")
    sys.exit(2)

ok, frame = capture.read()
capture.release()
if not ok or frame is None:
    print(f"Camera index {index} opened but did not return a frame")
    sys.exit(3)

print(f"Camera index {index} OK: {frame.shape[1]}x{frame.shape[0]}")
PY
