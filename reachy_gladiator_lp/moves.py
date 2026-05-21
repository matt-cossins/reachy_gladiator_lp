"""Gladiator move primitives for Reachy Mini.

Each move is a small, self-contained motion sequence executed via
`reachy_mini.goto_target(...)`. The catalogue is deliberately small so each
move is distinct and teachable.

Body-yaw spins gracefully degrade to head shakes if the SDK build does not
expose body_yaw on goto_target.
"""

from __future__ import annotations

import os
from typing import Callable

import numpy as np
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose

MOVE_DURATION_SCALE = float(os.getenv("REACHY_GLADIATOR_MOVE_DURATION_SCALE", "1.8"))


def _duration(seconds: float) -> float:
    return seconds * MOVE_DURATION_SCALE


def _safe_body_yaw(reachy_mini: ReachyMini, yaw_rad: float, duration: float, method: str = "minjerk") -> None:
    duration = _duration(duration)
    try:
        reachy_mini.goto_target(body_yaw=yaw_rad, duration=duration, method=method)
    except Exception:
        # Fallback: small head yaw nudge in the same direction
        reachy_mini.goto_target(
            head=create_head_pose(yaw=float(np.rad2deg(yaw_rad) * 0.2), degrees=True),
            duration=duration,
        )


# ---- Individual moves -----------------------------------------------------


def salute(reachy_mini: ReachyMini) -> None:
    """Stand tall, scan the crowd, then raise both antennas in salute."""
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-8, yaw=-18, roll=4, degrees=True),
        antennas=np.deg2rad([20, 8]),
        duration=_duration(0.32),
        method="ease_in_out",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-8, yaw=18, roll=-4, degrees=True),
        antennas=np.deg2rad([8, 20]),
        duration=_duration(0.32),
        method="ease_in_out",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-16, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([58, 58]),
        duration=_duration(0.42),
        method="minjerk",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-10, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([36, 36]),
        duration=_duration(0.34),
        method="minjerk",
    )


def bow(reachy_mini: ReachyMini) -> None:
    """Deep ceremonial bow."""
    reachy_mini.goto_target(
        head=create_head_pose(pitch=22, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([-20, 20]),
        duration=_duration(0.7),
        method="ease_in_out",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=0, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([0, 0]),
        duration=_duration(0.5),
        method="ease_in_out",
    )


def sword_swing(reachy_mini: ReachyMini) -> None:
    """Wind up, slash across the arena, then snap back to ready."""
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-4, yaw=32, roll=-18, degrees=True),
        antennas=np.deg2rad([52, -24]),
        duration=_duration(0.34),
        method="ease_in_out",
    )
    _safe_body_yaw(reachy_mini, np.deg2rad(28), 0.22, method="cartoon")
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-2, yaw=-34, roll=20, degrees=True),
        antennas=np.deg2rad([-24, 54]),
        duration=_duration(0.24),
        method="cartoon",
    )
    _safe_body_yaw(reachy_mini, np.deg2rad(-24), 0.22, method="cartoon")
    reachy_mini.goto_target(
        head=create_head_pose(pitch=6, yaw=-10, roll=8, degrees=True),
        antennas=np.deg2rad([-10, 38]),
        duration=_duration(0.24),
        method="cartoon",
    )
    _safe_body_yaw(reachy_mini, 0.0, 0.28, method="minjerk")
    reachy_mini.goto_target(
        head=create_head_pose(pitch=0, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([0, 0]),
        duration=_duration(0.28),
        method="minjerk",
    )


def shield_up(reachy_mini: ReachyMini) -> None:
    """Raise a crossed guard, absorb a hit, then peek over the shield."""
    reachy_mini.goto_target(
        head=create_head_pose(pitch=14, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([58, -58]),
        duration=_duration(0.34),
        method="ease_in_out",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=18, yaw=-10, roll=8, degrees=True),
        antennas=np.deg2rad([48, -48]),
        duration=_duration(0.22),
        method="cartoon",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=18, yaw=10, roll=-8, degrees=True),
        antennas=np.deg2rad([48, -48]),
        duration=_duration(0.22),
        method="cartoon",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-6, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([36, -36]),
        duration=_duration(0.30),
        method="minjerk",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=0, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([0, 0]),
        duration=_duration(0.26),
        method="minjerk",
    )


def battle_cry(reachy_mini: ReachyMini) -> None:
    """Big upward roar with brisk antenna shakes and head bobs."""
    cry_duration = lambda seconds: _duration(seconds * 0.72)
    reachy_mini.goto_target(
        head=create_head_pose(pitch=10, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([-28, -28]),
        duration=cry_duration(0.34),
        method="ease_in_out",
    )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-12, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([48, 48]),
        duration=cry_duration(0.42),
        method="ease_in_out",
    )
    for yaw, roll, left, right in [
        (-8, 5, 42, -42),
        (8, -5, -42, 42),
        (-7, 4, 36, -36),
        (7, -4, -36, 36),
    ]:
        reachy_mini.goto_target(
            head=create_head_pose(pitch=-8, yaw=yaw, roll=roll, degrees=True),
            antennas=np.deg2rad([left, right]),
            duration=cry_duration(0.28),
            method="ease_in_out",
        )
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-4, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([18, 18]),
        duration=cry_duration(0.40),
        method="minjerk",
    )


# ---- Verdict reactions ----------------------------------------------------


def victory(reachy_mini: ReachyMini) -> None:
    """Crowd loved it: excited antennas, controlled spin, then reset."""
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-8, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([35, 35]),
        duration=_duration(0.24),
        method="minjerk",
    )
    for left, right in [(-35, 35), (35, -35), (-30, 30), (30, -30)]:
        reachy_mini.goto_target(
            antennas=np.deg2rad([left, right]),
            duration=_duration(0.16),
            method="minjerk",
        )
    _safe_body_yaw(reachy_mini, np.deg2rad(45), 0.52, method="ease_in_out")
    _safe_body_yaw(reachy_mini, np.deg2rad(-45), 0.52, method="ease_in_out")
    _safe_body_yaw(reachy_mini, 0.0, 0.36, method="minjerk")
    reachy_mini.goto_target(
        head=create_head_pose(pitch=-6, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([0, 0]),
        duration=_duration(0.28),
        method="minjerk",
    )
    neutral(reachy_mini)


def defeat(reachy_mini: ReachyMini) -> None:
    """Crowd condemned: original slow bow defeat, then reset."""
    for pitch, ant in [(16, 55), (12, 50), (8, 45), (3, 40)]:
        reachy_mini.goto_target(
            head=create_head_pose(pitch=pitch, yaw=0, roll=0, degrees=True),
            antennas=np.deg2rad([-ant, ant]),
            duration=_duration(0.7),
            method="ease_in_out",
        )
    neutral(reachy_mini)


def neutral(reachy_mini: ReachyMini) -> None:
    """Ready stance, awaiting the emperor."""
    reachy_mini.goto_target(
        head=create_head_pose(pitch=0, yaw=0, roll=0, degrees=True),
        antennas=np.deg2rad([0, 0]),
        duration=_duration(0.6),
        method="ease_in_out",
    )


# ---- Move catalogue -------------------------------------------------------


MoveFn = Callable[[ReachyMini], None]

MOVE_DESCRIPTIONS: dict[str, str] = {
    "Salute": "Scans the crowd, lifts high, and holds a proud arena pose.",
    "Sword Swing": "Winds up wide, slashes across, and snaps back to ready.",
    "Shield Up": "Drops behind a crossed antenna guard and absorbs a hit.",
    "Battle Cry": "Throws its head up and rattles both antennas in a roar.",
}

MOVE_CATALOGUE: dict[str, MoveFn] = {
    "Salute": salute,
    "Sword Swing": sword_swing,
    "Shield Up": shield_up,
    "Battle Cry": battle_cry,
}
