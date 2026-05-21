<h1 align="center">
  <img src="reachy_gladiator_lp/static/media/reachy_gladiator_logo.png" alt="Reachy Gladiator" width="520">
</h1>

Reachy Gladiator LP is a learning-path Reachy Mini app: a laptop or desktop
runs the Reachy Mini MuJoCo simulation, while a Raspberry Pi with a USB webcam
runs the app, dashboard, and MediaPipe gesture recognition.

Reachy performs one gladiator move, settles into a ready stance, and waits for
your verdict. Give a thumbs up for victory or a thumbs down for defeat.

![Illustration of Reachy Mini in a gladiator style pose.](reachy_gladiator_lp/static/media/reachy_gladiator.png "Reachy Mini Gladiator App Concept")

The full Arm Learning Path walks through the setup step by step. This README is
the quick project overview and visual reference.

## Moves

| Salute | Sword Swing |
| --- | --- |
| <img src="reachy_gladiator_lp/static/media/salute.gif" alt="Reachy Mini performing the Salute move" width="360"> | <img src="reachy_gladiator_lp/static/media/sword.gif" alt="Reachy Mini performing the Sword Swing move" width="360"> |

| Shield Up | Battle Cry |
| --- | --- |
| <img src="reachy_gladiator_lp/static/media/shield.gif" alt="Reachy Mini performing the Shield Up move" width="360"> | <img src="reachy_gladiator_lp/static/media/battle-cry.gif" alt="Reachy Mini performing the Battle Cry move" width="360"> |

## Verdicts

| Thumbs Up: Victory | Thumbs Down: Defeat |
| --- | --- |
| <img src="reachy_gladiator_lp/static/media/thumbs-up.gif" alt="Reachy Mini reacting to a thumbs-up verdict with a victory animation" width="360"> | <img src="reachy_gladiator_lp/static/media/thumbs-down.gif" alt="Reachy Mini reacting to a thumbs-down verdict with a defeat animation" width="360"> |

## Quick Run

Start the simulator on your laptop or desktop:

```bash
cd ~/reachy_projects/reachy_gladiator_lp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip "reachy-mini[mujoco]"
REACHY_SIM_PORT=18000 ./scripts/start_sim.sh
```

Leave that terminal running, then find the simulation host IP address.

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

Open the dashboard:

```text
http://<pi-ip>:8042
```

## Useful Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `REACHY_SIM_PORT` | `8000` | Simulation daemon port. The Learning Path uses `18000`. |
| `REACHY_GLADIATOR_DAEMON_HOST` | required | Simulation host IP or hostname used by the Pi app. |
| `REACHY_GLADIATOR_DAEMON_PORT` | `8000` | Simulation or physical daemon port used by the Pi app. |
| `REACHY_GLADIATOR_DAEMON_TIMEOUT` | `8.0` | SDK connection timeout in seconds. |
| `REACHY_GLADIATOR_DASHBOARD_PORT` | `8042` | Dashboard port served from the Pi. |
| `REACHY_GLADIATOR_MEDIA_BACKEND` | `no_media` | Use `no_media` for Pi USB webcam. Use `reachy` for daemon camera media. |
| `REACHY_GLADIATOR_CAMERA` | `opencv` | Use `opencv`, `reachy`, or `auto` for gesture frames. |
| `REACHY_GLADIATOR_CAMERA_INDEX` | `0` | USB webcam index for OpenCV. |

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
│   │   └── gesture_recognizer.task
│   └── static/
│       ├── index.html
│       ├── main.js
│       ├── style.css
│       └── media/
└── pyproject.toml
```
