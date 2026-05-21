"""MediaPipe thumbs up/down detection.

The recognizer runs in a small worker process. This keeps the Reachy app alive
if MediaPipe's native graphics setup is unavailable in a simulator/headless
environment.
"""

from __future__ import annotations

import multiprocessing as mp_process
import os
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from typing import Any

import numpy as np

GESTURE_WORKER_STARTUP_TIMEOUT_S = float(
    os.getenv("REACHY_GLADIATOR_GESTURE_STARTUP_TIMEOUT_S", "30.0")
)
GESTURE_BACKEND = os.getenv("REACHY_GLADIATOR_GESTURE_BACKEND", "auto").strip().lower()


@dataclass(slots=True)
class GestureResult:
    label: str | None  # "thumbs_up" | "thumbs_down" | None
    x_px: int
    y_px: int
    confidence: float


class ThumbGestureDetector:
    """Single-frame thumb gesture detector backed by MediaPipe Tasks."""

    def __init__(self, model_path: Path | None = None) -> None:
        if model_path is None:
            model_path = Path(__file__).resolve().parent / "assets" / "gesture_recognizer.task"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Missing gesture model at {model_path}. "
                "Download MediaPipe gesture_recognizer.task into "
                "reachy_gladiator_lp/assets/."
            )

        self._inline_recognizer: Any | None = None
        self._worker = self._use_worker()
        if not self._worker:
            self._start_inline(model_path)
            return

        context = mp_process.get_context("spawn")
        self._request_q: mp_process.Queue[Any] = context.Queue(maxsize=1)
        self._response_q: mp_process.Queue[Any] = context.Queue(maxsize=1)
        self._process = context.Process(
            target=_gesture_worker,
            args=(str(model_path), self._request_q, self._response_q),
            daemon=True,
        )
        self._process.start()
        self._await_ready()

    def _use_worker(self) -> bool:
        if GESTURE_BACKEND == "inline":
            return False
        return True

    def _start_inline(self, model_path: Path) -> None:
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._inline_recognizer = vision.GestureRecognizer.create_from_options(options)

    def _await_ready(self) -> None:
        deadline = time.monotonic() + GESTURE_WORKER_STARTUP_TIMEOUT_S
        message: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            try:
                message = self._response_q.get(timeout=0.2)
                break
            except queue.Empty as exc:
                if not self._process.is_alive():
                    raise RuntimeError("MediaPipe gesture worker exited during startup") from exc
        if message is None:
            self.close()
            raise RuntimeError("MediaPipe gesture worker did not become ready")

        if message.get("type") == "ready":
            return
        if message.get("type") == "error":
            raise RuntimeError(message.get("message", "MediaPipe gesture worker failed"))
        raise RuntimeError(f"Unexpected gesture worker message: {message!r}")

    def detect(self, bgr_frame: np.ndarray) -> GestureResult:
        height, width = bgr_frame.shape[:2]
        if not self._worker:
            import mediapipe as mp

            if self._inline_recognizer is None:
                return GestureResult(label=None, x_px=width // 2, y_px=height // 2, confidence=0.0)
            return _gesture_result_from_detection(self._inline_recognizer, mp, bgr_frame)

        if not self._process.is_alive():
            return GestureResult(label=None, x_px=width // 2, y_px=height // 2, confidence=0.0)

        self._clear_queue(self._request_q)
        self._request_q.put(bgr_frame, timeout=0.2)

        try:
            message = self._response_q.get(timeout=2.0)
        except queue.Empty:
            return GestureResult(label=None, x_px=width // 2, y_px=height // 2, confidence=0.0)

        if message.get("type") != "result":
            return GestureResult(label=None, x_px=width // 2, y_px=height // 2, confidence=0.0)

        return GestureResult(
            label=message["label"],
            x_px=message["x_px"],
            y_px=message["y_px"],
            confidence=message["confidence"],
        )

    def close(self) -> None:
        if not self._worker:
            if self._inline_recognizer is not None:
                self._inline_recognizer.close()
                self._inline_recognizer = None
            return

        if self._process.is_alive():
            try:
                self._request_q.put(None, timeout=0.2)
            except Exception:
                pass
            self._process.join(timeout=1.0)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)

    @staticmethod
    def _clear_queue(items: mp_process.Queue[Any]) -> None:
        try:
            while True:
                items.get_nowait()
        except queue.Empty:
            return


def _gesture_worker(
    model_path: str,
    request_q: mp_process.Queue[Any],
    response_q: mp_process.Queue[Any],
) -> None:
    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(Path(gettempdir()) / "reachy_gladiator_lp_mpl"),
    )

    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    recognizer = None
    try:
        base_options = python.BaseOptions(
            model_asset_path=model_path,
            delegate=python.BaseOptions.Delegate.CPU,
        )
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        recognizer = vision.GestureRecognizer.create_from_options(options)
        response_q.put({"type": "ready"})

        while True:
            bgr_frame = request_q.get()
            if bgr_frame is None:
                return
            response_q.put(_detect_frame(recognizer, mp, bgr_frame))
    except Exception as exc:
        response_q.put({"type": "error", "message": str(exc)})
    finally:
        if recognizer is not None:
            recognizer.close()


def _detect_frame(recognizer: Any, mediapipe: Any, bgr_frame: np.ndarray) -> dict[str, Any]:
    result = _gesture_result_from_detection(recognizer, mediapipe, bgr_frame)
    return {
        "type": "result",
        "label": result.label,
        "x_px": result.x_px,
        "y_px": result.y_px,
        "confidence": result.confidence,
    }


def _gesture_result_from_detection(
    recognizer: Any,
    mediapipe: Any,
    bgr_frame: np.ndarray,
) -> GestureResult:
    height, width = bgr_frame.shape[:2]
    rgb_frame = bgr_frame[:, :, ::-1].copy()
    mp_image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB, data=rgb_frame)
    result = recognizer.recognize(mp_image)

    if not result.gestures:
        return GestureResult(label=None, x_px=width // 2, y_px=height // 2, confidence=0.0)

    top = result.gestures[0][0]
    raw_label = top.category_name
    confidence = float(top.score)

    if raw_label == "Thumb_Up":
        label = "thumbs_up"
    elif raw_label == "Thumb_Down":
        label = "thumbs_down"
    else:
        label = None

    if result.hand_landmarks:
        thumb_tip = result.hand_landmarks[0][4]
        x_px = int(np.clip(thumb_tip.x * width, 0, width - 1))
        y_px = int(np.clip(thumb_tip.y * height, 0, height - 1))
    else:
        x_px = width // 2
        y_px = height // 2

    return GestureResult(label=label, x_px=x_px, y_px=y_px, confidence=confidence)
