---
title: Reachy Gladiator LP
emoji: ⚔️
colorFrom: red
colorTo: yellow
sdk: static
pinned: false
short_description: Pi webcam and MuJoCo learning path for Reachy Mini
tags:
  - reachy_mini
  - reachy_mini_python_app
  - raspberry_pi
  - mujoco
---

<h1 align="center">
  <img src="reachy_gladiator_lp/static/media/reachy_gladiator_logo.png" alt="Reachy Gladiator" width="520">
</h1>

Reachy Gladiator LP is the learning-path version of Reachy Gladiator. It keeps
the same app behavior as the packaged Hugging Face Space, but is arranged for a
distributed edge robotics workflow:

- a laptop or desktop runs the Reachy Mini MuJoCo simulation,
- a Raspberry Pi runs the app, dashboard, USB webcam capture, and MediaPipe
  gesture recognition,
- the Pi sends motion commands to the simulation host through the Reachy Mini
  SDK.

Reachy performs one gladiator move, waits for your verdict, and reacts to a
thumbs up or thumbs down.

![Illustration of Reachy Mini in a gladiator arena.](reachy_gladiator_lp/static/media/reachy_gladiator.png "Reachy Mini Gladiator App Concept")

## Quick Run

Start the simulator on your laptop or desktop:

```bash
cd ~/reachy_projects/reachy_gladiator_lp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip "reachy-mini[mujoco]"
REACHY_SIM_PORT=18000 ./scripts/start_sim.sh
```

On the Raspberry Pi:

```bash
cd ~/reachy_projects
git clone https://github.com/matt-cossins/reachy_gladiator_lp.git
cd reachy_gladiator_lp
./scripts/setup_pi.sh
source .venv/bin/activate
./scripts/check_pi_camera.sh
REACHY_GLADIATOR_DAEMON_PORT=18000 ./scripts/run_pi_app.sh <simulation-host-ip>
```

Open the dashboard from your browser:

```text
http://<pi-ip>:8042
```

## Useful Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `REACHY_SIM_PORT` | `8000` | Simulation daemon port. The Learning Path uses `18000`. |
| `REACHY_GLADIATOR_DAEMON_HOST` | required by `run_pi_app.sh` | Simulation or physical daemon host used by the Pi app. |
| `REACHY_GLADIATOR_DAEMON_PORT` | `8000` | Daemon port used by the Pi app. |
| `REACHY_GLADIATOR_DAEMON_TIMEOUT` | `8.0` | SDK connection timeout in seconds. |
| `REACHY_GLADIATOR_DASHBOARD_PORT` | `8042` | Dashboard port served from the Pi. |
| `REACHY_GLADIATOR_MEDIA_BACKEND` | `no_media` | Use `no_media` for Pi USB webcam. Use `reachy` for daemon camera media. |
| `REACHY_GLADIATOR_CAMERA` | `opencv` | Use `opencv`, `reachy`, or `auto` for gesture frames. |
| `REACHY_GLADIATOR_CAMERA_INDEX` | `0` | USB webcam index for OpenCV. |

## Physical Reachy Route

For a physical Reachy Mini, first try the packaged Hugging Face app through
Reachy Mini Control. To adapt this source project instead, keep the same app
logic and switch the source of camera frames and daemon media:

```bash
REACHY_GLADIATOR_MEDIA_BACKEND=reachy \
REACHY_GLADIATOR_CAMERA=reachy \
REACHY_GLADIATOR_DAEMON_PORT=8000 \
./scripts/run_pi_app.sh localhost
```

Use the daemon host and port that match your physical Reachy setup. Start with
`neutral()` or one safe move before running the full loop on hardware.

## Project Shape

```text
reachy_gladiator_lp/
├── scripts/
│   ├── setup_pi.sh
│   ├── start_sim.sh
│   ├── check_pi_camera.sh
│   └── run_pi_app.sh
├── reachy_gladiator_lp/
│   ├── main.py
│   ├── camera.py
│   ├── gesture.py
│   ├── moves.py
│   ├── assets/
│   └── static/
```

The Reachy Mini app entry point is:

```toml
[project.entry-points."reachy_mini_apps"]
reachy-gladiator-lp = "reachy_gladiator_lp.main:ReachyGladiatorLp"
```
