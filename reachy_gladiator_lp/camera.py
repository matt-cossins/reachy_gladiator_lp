"""Frame sources for Reachy Gladiator LP.

The default learning-path route uses OpenCV to read a USB webcam attached to
the Raspberry Pi. Physical Reachy experiments can switch to SDK media frames
from the Reachy daemon with ``REACHY_GLADIATOR_CAMERA=reachy``.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

import numpy as np
from reachy_mini import ReachyMini

logger = logging.getLogger(__name__)


class FrameSource(Protocol):
    name: str

    def get_frame(self) -> np.ndarray | None:
        """Return one BGR frame, or None when no frame is available."""

    def close(self) -> None:
        """Release source resources."""


class ReachyMediaFrameSource:
    """Read frames from the Reachy daemon media pipeline."""

    name = "reachy"

    def __init__(self, reachy_mini: ReachyMini) -> None:
        self._reachy_mini = reachy_mini

    def get_frame(self) -> np.ndarray | None:
        if getattr(self._reachy_mini.media, "camera", None) is None:
            return None
        return self._reachy_mini.media.get_frame()

    def close(self) -> None:
        pass


class OpenCVCameraFrameSource:
    """Read frames from the host webcam using OpenCV capture only."""

    name = "opencv"

    def __init__(self, camera_index: int = 0) -> None:
        import cv2

        self._cv2 = cv2
        self._capture = cv2.VideoCapture(camera_index)
        if not self._capture.isOpened():
            self._capture.release()
            raise RuntimeError(f"Could not open local webcam index {camera_index}")

    def get_frame(self) -> np.ndarray | None:
        ok, frame = self._capture.read()
        return frame if ok else None

    def close(self) -> None:
        self._capture.release()


def select_frame_source(reachy_mini: ReachyMini) -> FrameSource:
    """Select the frame source for thumb detection.

    ``REACHY_GLADIATOR_CAMERA`` accepts:
    - ``opencv``: default. Use the Pi or host USB webcam.
    - ``reachy``: use SDK media frames from the Reachy daemon.
    - ``auto``: use OpenCV in simulation/mockup, otherwise SDK media when available.
    """

    requested = os.getenv("REACHY_GLADIATOR_CAMERA", "opencv").strip().lower()
    if requested not in {"auto", "reachy", "opencv"}:
        logger.warning(
            "Unknown REACHY_GLADIATOR_CAMERA=%r; falling back to auto.",
            requested,
        )
        requested = "opencv"

    if requested == "opencv":
        return OpenCVCameraFrameSource(_camera_index())

    if requested == "reachy":
        if _sdk_media_camera_available(reachy_mini):
            return ReachyMediaFrameSource(reachy_mini)
        logger.warning("SDK media camera is unavailable; using direct OpenCV camera")
        return OpenCVCameraFrameSource(_camera_index())

    if getattr(reachy_mini, "media_released", False) or _daemon_is_simulated(reachy_mini):
        try:
            return OpenCVCameraFrameSource(_camera_index())
        except Exception:
            logger.exception("Could not open local webcam; falling back to Reachy media")

    if _sdk_media_camera_available(reachy_mini):
        return ReachyMediaFrameSource(reachy_mini)

    return ReachyMediaFrameSource(reachy_mini)


def _camera_index() -> int:
    raw = os.getenv("REACHY_GLADIATOR_CAMERA_INDEX", "0").strip()
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid REACHY_GLADIATOR_CAMERA_INDEX=%r; using 0.", raw)
        return 0


def _sdk_media_camera_available(reachy_mini: ReachyMini) -> bool:
    return getattr(getattr(reachy_mini, "media", None), "camera", None) is not None


def _daemon_is_simulated(reachy_mini: ReachyMini) -> bool:
    try:
        status = reachy_mini.client.get_status(wait=False)
    except Exception:
        return False
    return bool(
        getattr(status, "simulation_enabled", False)
        or getattr(status, "mockup_sim_enabled", False)
    )
