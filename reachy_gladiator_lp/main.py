"""Reachy Gladiator learning-path app.

The default route runs on a Raspberry Pi with a USB webcam and sends motion
commands to a Reachy Mini daemon running on a development machine with MuJoCo
simulation enabled. Environment variables can switch the same code toward a
physical Reachy daemon and SDK camera media.
"""

from __future__ import annotations

import logging
import json
import os
import random
import threading
import time
from typing import Any

import numpy as np
from fastapi.responses import StreamingResponse
from reachy_mini import ReachyMini, ReachyMiniApp

from . import moves as gmoves
from .camera import FrameSource, select_frame_source
from .gesture import ThumbGestureDetector

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# --- Tunables --------------------------------------------------------------

MOVES_PER_ROUND = 1
MOVE_REPETITIONS = 3
VERDICT_MIN_CONFIDENCE = 0.55
GESTURE_RETRY_INTERVAL_S = 2.0
LOOP_SLEEP_S = 0.05
INTER_ROUND_PAUSE_S = 0.25
POST_VERDICT_HOLD_S = 0.5
STARTUP_DELAY_S = 10.0
GESTURE_WARMUP_WAIT_S = 0.5
DASHBOARD_PREVIEW_MAX_WIDTH = 640
DASHBOARD_PREVIEW_JPEG_QUALITY = 72
DASHBOARD_PREVIEW_SLEEP_S = 0.04


def _request_media_backend_from_env() -> str | None:
    raw = os.getenv("REACHY_GLADIATOR_MEDIA_BACKEND", "no_media").strip().lower()
    if raw in {"no_media", "none", "off", "disabled"}:
        return "no_media"
    if raw in {"reachy", "sdk", "daemon", "media"}:
        return None
    logger.warning(
        "Unknown REACHY_GLADIATOR_MEDIA_BACKEND=%r; using no_media.",
        raw,
    )
    return "no_media"


def _initial_status() -> dict[str, Any]:
    return {
        "state": "starting",
        "round": 0,
        "sequence": [],
        "active_move": None,
        "current_repeat": 0,
        "repeat_count": MOVE_REPETITIONS,
        "countdown": None,
        "moves": gmoves.MOVE_DESCRIPTIONS,
        "verdict": None,
        "gesture": None,
        "confidence": 0.0,
        "camera_ready": False,
        "camera_source": None,
    }


class ReachyGladiatorLp(ReachyMiniApp):
    """Pi/webcam learning-path app with remote daemon support."""

    custom_app_url: str | None = "http://0.0.0.0:8042"
    request_media_backend: str | None = "no_media"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        dashboard_host = os.getenv("REACHY_GLADIATOR_DASHBOARD_HOST", "0.0.0.0")
        dashboard_port = os.getenv("REACHY_GLADIATOR_DASHBOARD_PORT", "8042")
        self.custom_app_url = f"http://{dashboard_host}:{dashboard_port}"
        self.request_media_backend = _request_media_backend_from_env()
        self._state_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._status: dict[str, Any] = _initial_status()
        super().__init__(*args, **kwargs)
        self._register_dashboard_routes()

    def _register_dashboard_routes(self) -> None:
        if self.settings_app is None:
            return

        @self.settings_app.get("/status")
        def get_status() -> dict[str, Any]:
            with self._state_lock:
                return dict(self._status)

        @self.settings_app.get("/events")
        def events() -> StreamingResponse:
            return StreamingResponse(
                self._status_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        @self.settings_app.get("/video")
        def video() -> StreamingResponse:
            return StreamingResponse(
                self._video_stream(self._read_frame),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

    def _update_status(self, **values: Any) -> None:
        with self._state_lock:
            self._status.update(values)

    def _reset_status(self) -> None:
        with self._state_lock:
            self._status = _initial_status()

    def _update_frame(self, frame: np.ndarray) -> None:
        with self._frame_lock:
            self._latest_frame = frame.copy()

    def _read_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        rng = random.Random()
        move_queue: list[str] = []
        last_move: str | None = None
        round_idx = 0
        detector: ThumbGestureDetector | None = None
        detector_warmup_done = threading.Event()
        detector_warmup_lock = threading.Lock()
        detector_warmup: dict[str, ThumbGestureDetector | None] = {"detector": None}
        capture_stop = threading.Event()
        self._latest_frame = None
        self._reset_status()

        def capture_frames(frame_source: FrameSource) -> None:
            while not stop_event.is_set() and not capture_stop.is_set():
                try:
                    frame = frame_source.get_frame()
                except Exception:
                    logger.exception("Camera frame capture failed")
                    time.sleep(LOOP_SLEEP_S)
                    continue

                if frame is None:
                    time.sleep(LOOP_SLEEP_S)
                    continue

                self._update_frame(frame)
                self._update_status(camera_ready=True)
                time.sleep(LOOP_SLEEP_S)

        def warmup_detector() -> None:
            warmed_detector: ThumbGestureDetector | None = None
            try:
                warmed_detector = ThumbGestureDetector()
                while not stop_event.is_set() and not capture_stop.is_set():
                    frame = self._read_frame()
                    if frame is not None:
                        warmed_detector.detect(frame)
                        break
                    time.sleep(LOOP_SLEEP_S)
                with detector_warmup_lock:
                    detector_warmup["detector"] = warmed_detector
                    warmed_detector = None
            except Exception:
                logger.exception("Gesture detector warmup failed")
            finally:
                if warmed_detector is not None:
                    warmed_detector.close()
                detector_warmup_done.set()

        logger.info("Reachy Gladiator entering the arena")
        self._update_status(state="neutral")
        frame_source = select_frame_source(reachy_mini)
        logger.info("Using %s frame source for MediaPipe gestures", frame_source.name)
        self._update_status(camera_source=frame_source.name)
        capture_thread = threading.Thread(
            target=capture_frames,
            args=(frame_source,),
            name="gladiator-camera",
            daemon=True,
        )
        capture_thread.start()
        detector_warmup_thread = threading.Thread(
            target=warmup_detector,
            name="gladiator-gesture-warmup",
            daemon=True,
        )
        detector_warmup_thread.start()

        try:
            gmoves.neutral(reachy_mini)
            startup_deadline = time.monotonic() + STARTUP_DELAY_S
            while not stop_event.is_set() and time.monotonic() < startup_deadline:
                self._update_status(
                    state="preparing",
                    countdown=max(0, int(np.ceil(startup_deadline - time.monotonic()))),
                )
                time.sleep(LOOP_SLEEP_S)

            while not stop_event.is_set():
                round_idx += 1

                sequence = self._build_sequence(rng, move_queue, last_move)
                last_move = sequence[-1]
                logger.info(
                    "Round %d performing: %s x%d",
                    round_idx,
                    sequence[0],
                    MOVE_REPETITIONS,
                )
                self._update_status(
                    state="performing",
                    round=round_idx,
                    sequence=sequence,
                    active_move=sequence[0],
                    current_repeat=1,
                    repeat_count=MOVE_REPETITIONS,
                    countdown=None,
                    verdict=None,
                    gesture=None,
                    confidence=0.0,
                )
                for name in sequence:
                    if stop_event.is_set():
                        return
                    move_fn = gmoves.MOVE_CATALOGUE[name]
                    for repeat_idx in range(1, MOVE_REPETITIONS + 1):
                        if stop_event.is_set():
                            return
                        self._update_status(active_move=name, current_repeat=repeat_idx)
                        try:
                            move_fn(reachy_mini)
                        except Exception:
                            logger.exception(
                                "Move %s repeat %d failed; continuing",
                                name,
                                repeat_idx,
                            )

                gmoves.neutral(reachy_mini)
                self._update_status(
                    state="awaiting_verdict",
                    active_move=None,
                    current_repeat=0,
                )
                if detector is None:
                    detector_warmup_done.wait(timeout=GESTURE_WARMUP_WAIT_S)
                    with detector_warmup_lock:
                        detector = detector_warmup["detector"]
                        detector_warmup["detector"] = None
                verdict, detector = self._await_verdict(
                    reachy_mini,
                    self._read_frame,
                    detector,
                    stop_event,
                    self._update_status,
                )

                if verdict == "thumbs_up":
                    logger.info("Round %d: VICTORY", round_idx)
                    self._update_status(
                        state="victory",
                        verdict=verdict,
                        active_move=None,
                        current_repeat=0,
                    )
                    gmoves.victory(reachy_mini)
                elif verdict == "thumbs_down":
                    logger.info("Round %d: DEFEAT", round_idx)
                    self._update_status(
                        state="defeat",
                        verdict=verdict,
                        active_move=None,
                        current_repeat=0,
                    )
                    gmoves.defeat(reachy_mini)
                else:
                    return

                if stop_event.is_set():
                    return

                time.sleep(POST_VERDICT_HOLD_S)
                time.sleep(INTER_ROUND_PAUSE_S)
        finally:
            capture_stop.set()
            capture_thread.join(timeout=1.0)
            detector_warmup_thread.join(timeout=1.0)
            frame_source.close()
            with detector_warmup_lock:
                warmed_detector = detector_warmup["detector"]
                detector_warmup["detector"] = None
            if warmed_detector is not None and warmed_detector is not detector:
                warmed_detector.close()
            if detector is not None:
                detector.close()
            try:
                gmoves.neutral(reachy_mini)
            except Exception:
                pass

    # -- helpers ------------------------------------------------------------

    def _build_sequence(
        self,
        rng: random.Random,
        move_queue: list[str],
        last_move: str | None,
    ) -> list[str]:
        names = list(gmoves.MOVE_CATALOGUE.keys())
        if not move_queue:
            move_queue.extend(rng.sample(names, len(names)))
            if last_move is not None and len(move_queue) > 1 and move_queue[0] == last_move:
                move_queue.append(move_queue.pop(0))

        return [move_queue.pop(0)]

    def _await_verdict(
        self,
        reachy_mini: ReachyMini,
        read_frame: Any,
        detector: ThumbGestureDetector | None,
        stop_event: threading.Event,
        update_status: Any,
    ) -> tuple[str | None, ThumbGestureDetector | None]:
        """Watch the camera for a thumbs up/down."""
        last_label: str | None = None
        consecutive = 0
        next_detector_retry = 0.0

        while not stop_event.is_set():
            frame = read_frame()
            if frame is None:
                time.sleep(LOOP_SLEEP_S)
                continue

            if detector is None:
                now = time.monotonic()
                if now < next_detector_retry:
                    time.sleep(LOOP_SLEEP_S)
                    continue
                try:
                    detector = ThumbGestureDetector()
                except Exception:
                    logger.exception("Gesture detector failed to start")
                    update_status(gesture="unavailable", confidence=0.0)
                    next_detector_retry = now + GESTURE_RETRY_INTERVAL_S
                    time.sleep(LOOP_SLEEP_S)
                    continue

            result = detector.detect(frame)
            update_status(
                gesture=result.label,
                confidence=result.confidence,
            )

            if (
                result.label in ("thumbs_up", "thumbs_down")
                and result.confidence >= VERDICT_MIN_CONFIDENCE
            ):
                if result.label == last_label:
                    consecutive += 1
                else:
                    last_label = result.label
                    consecutive = 1
                if consecutive >= 2:
                    return result.label, detector
            else:
                last_label = None
                consecutive = 0

            time.sleep(LOOP_SLEEP_S)

        return None, detector

    def _video_stream(self, read_frame: Any) -> Any:
        import cv2

        while not self.stop_event.is_set():
            frame = read_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            preview_frame = self._resize_preview_frame(frame)
            ok, encoded = cv2.imencode(
                ".jpg",
                preview_frame,
                [cv2.IMWRITE_JPEG_QUALITY, DASHBOARD_PREVIEW_JPEG_QUALITY],
            )
            if not ok:
                time.sleep(0.1)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {encoded.nbytes}\r\n\r\n".encode("ascii")
                + encoded.tobytes()
                + b"\r\n"
            )
            time.sleep(DASHBOARD_PREVIEW_SLEEP_S)

    def _status_stream(self) -> Any:
        last_payload: str | None = None
        last_heartbeat = 0.0

        while not self.stop_event.is_set():
            with self._state_lock:
                payload = json.dumps(self._status, separators=(",", ":"))

            now = time.monotonic()
            if payload != last_payload or now - last_heartbeat >= 1.0:
                yield f"data: {payload}\n\n".encode("utf-8")
                last_payload = payload
                last_heartbeat = now

            time.sleep(0.08)

    def _resize_preview_frame(self, frame: np.ndarray) -> np.ndarray:
        import cv2

        height, width = frame.shape[:2]
        if width <= DASHBOARD_PREVIEW_MAX_WIDTH:
            return frame

        scale = DASHBOARD_PREVIEW_MAX_WIDTH / width
        preview_size = (DASHBOARD_PREVIEW_MAX_WIDTH, max(1, int(height * scale)))
        return cv2.resize(frame, preview_size, interpolation=cv2.INTER_AREA)


ReachyGladiatorLP = ReachyGladiatorLp
ReachyGladiatorLPApp = ReachyGladiatorLp
ReachyGladiatorApp = ReachyGladiatorLp


if __name__ == "__main__":
    daemon_host = os.getenv("REACHY_GLADIATOR_DAEMON_HOST", "localhost")
    daemon_port = int(os.getenv("REACHY_GLADIATOR_DAEMON_PORT", "8000"))
    daemon_timeout = float(os.getenv("REACHY_GLADIATOR_DAEMON_TIMEOUT", "8.0"))
    os.environ.setdefault("REACHY_GLADIATOR_CAMERA", "opencv")
    os.environ.setdefault("REACHY_GLADIATOR_MEDIA_BACKEND", "no_media")
    app = ReachyGladiatorLp()
    try:
        app.wrapped_run(host=daemon_host, port=daemon_port, timeout=daemon_timeout)
    except KeyboardInterrupt:
        app.stop()
