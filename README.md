# ARGUS — Autonomous Risk Guardian Unified System

ARGUS is a disaster-response sensor platform built for an AI/ML hackathon. It combines edge sensor nodes, on-device computer vision, and a rolling-baseline risk engine to flag anomalous conditions (temperature spikes, structural shifts, presence of people) at a monitored site, and surfaces it all on a live dashboard with AI-generated explanations of what's happening and why.

> ⚠️ **Hackathon project** — built for a demo, not production. See [Known Limitations](#known-limitations) before relying on this for anything real.

---

## Table of contents

- [Architecture](#architecture)
- [Components](#components)
- [Getting started](#getting-started)
  - [Backend](#1-backend-fastapi)
  - [Raspberry Pi camera node](#2-raspberry-pi-camera-node)
  - [ESP32 sensor node](#3-esp32-sensor-node)
  - [Dashboard](#4-dashboard-reactvite)
- [API reference](#api-reference)
- [Risk engine](#risk-engine)
- [Environment variables](#environment-variables)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Architecture

```
┌─────────────┐      sensor readings       ┌──────────────────┐
│   ESP32     │ ──────────────────────────▶ │                  │
│  (firmware, │      POST /api/sensor-data  │                  │
│  DHT11,     │                              │                  │
│  HC-SR04,   │                              │   FastAPI        │      ┌─────────────┐
│  IR beam)   │                              │   backend        │◀────▶│  SQLite/DB   │
└─────────────┘                              │                  │      └─────────────┘
                                              │  • risk_engine   │
┌─────────────┐    snapshot + detections     │  • ai_explainer  │
│ Raspberry Pi│ ──────────────────────────▶  │    (Gemini)      │
│  + Camera   │      POST /api/image         │                  │
│  Module     │                              └──────────────────┘
│  (YOLOv8n)  │                                        ▲
└─────────────┘                                        │ REST polling
                                                         │
                                              ┌──────────────────┐
                                              │  React/Vite      │
                                              │  dashboard        │
                                              │  • node map       │
                                              │  • risk panels     │
                                              │  • camera feed      │
                                              │  • AI explanations   │
                                              └──────────────────┘
```

Each physical node (ESP32 + Pi, co-located) reports independently to the backend, which persists readings, recomputes risk on every new data point, and exposes it all over a REST API the dashboard polls.

## Components

| Component | Stack | Role |
|---|---|---|
| **ESP32 firmware** | PlatformIO / C++ | Reads DHT11 (temp/humidity), HC-SR04 (distance/structural shift), IR beam (obstruction), reports device health, POSTs to backend |
| **Raspberry Pi server** | Python, OpenCV, Ultralytics YOLOv8n, Picamera2 | Captures camera frames, runs person detection, POSTs snapshots + detection flags to backend |
| **Backend** | FastAPI, SQLAlchemy | Ingests sensor/image data, runs the risk engine, serves the REST API, generates AI explanations via Claude |
| **Dashboard** | React, Vite | Live view of node status, risk levels, camera snapshots, alerts, and AI-generated situation summaries |

---

## Project structure

```
ARGUS/
├── backend/
│   ├── main.py                 # FastAPI app, all routes
│   ├── database.py             # SQLAlchemy models + session
│   ├── risk_engine.py          # rolling z-score risk computation
│   ├── ai_explainer.py         # Claude-based explanations
│   ├── fusion.py                # sensor/camera signal fusion
│   ├── seed.py                  # seed data for demos
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── argus.db                 # SQLite database (gitignored in prod)
│   └── uploads/                 # camera snapshots, served at /uploads
├── pi-server/
│   ├── detect_server.py         # capture + YOLOv8n + upload loop (runs on the Pi)
│   ├── camera_uploader.py
│   ├── sensor_fusion.py
│   ├── server.py
│   ├── simulate_nodes.py        # simulate multiple nodes without hardware
│   ├── mock_sensor.py           # simulate sensor data without an ESP32
│   ├── seed_stimulation.py
│   ├── update_setup_database.sql
│   ├── requirements.txt
│   └── Dockerfile
├── esp32-sensor-node/            # PlatformIO firmware
├── dashboard/                     # React/Vite frontend
├── docker-compose.yml
└── argus_config.json
```

> Each of `backend/` and `pi-server/` has its own `README.md` with folder-specific details — this top-level README covers how the pieces fit together.

## Getting started

### Option A — Docker Compose (fastest)

If you just want the backend + Pi-server pieces running together without wrangling Python environments:

```bash
docker compose up --build
```

Check `docker-compose.yml` and `argus_config.json` for the exact ports and environment variables it wires up — update them there if your setup differs from the defaults below.

### Option B — Run each piece manually

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/` if you want AI explanations enabled:
```
ANTHROPIC_API_KEY=your-key-here
```

Run it:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> `--host 0.0.0.0` matters if the ESP32 or Pi need to reach this backend over the local network — binding to `127.0.0.1` only accepts connections from the same machine.

The backend auto-creates its upload directory and initializes the database on startup (`database.init_db()`).

### 2. Raspberry Pi camera node

The Pi Camera Module (CSI ribbon cable) runs on the `libcamera` stack, which requires **Picamera2** rather than `cv2.VideoCapture` directly.

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-libcamera

cd pi-server
python3 -m venv --system-site-packages venv   # --system-site-packages is required so the venv can see picamera2
source venv/bin/activate
pip install -r requirements.txt
```

Verify the camera is detected before running anything:
```bash
libcamera-still -o test.jpg
```

Run the detection/upload script:
```bash
export BACKEND_URL=http://<backend-host-ip>:8000
export NODE_ID=ARGUS-01
python detect_server.py
```

This captures a frame, runs YOLOv8n person detection, and POSTs a JPEG snapshot + detection flags to the backend every 5 seconds.

**No Pi or camera hardware on hand?** `simulate_nodes.py` and `mock_sensor.py` let you exercise the backend and dashboard without physical hardware — useful for demo prep or dashboard development away from the rig.

### 3. ESP32 sensor node

Firmware lives in `esp32-sensor-node/`, built with PlatformIO.

```bash
cd esp32-sensor-node
pio run --target upload
pio device monitor
```

Configure WiFi credentials and the backend URL in the firmware's config header before flashing. On boot, the ESP32 prints its assigned IP over serial — useful for debugging connectivity, though the ESP32 only needs *outbound* access to the backend, not an inbound port.

### 4. Dashboard (React/Vite)

```bash
cd dashboard
npm install
```

Create a `.env` file:
```
VITE_BACKEND_URL=http://<backend-host-ip>:8000
```

Run it:
```bash
npm run dev
```

---

## API reference

All endpoints are served by the FastAPI backend on port `8000` by default.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/nodes` | List all known nodes |
| `GET` | `/api/nodes/{node_id}` | Detail for one node |
| `GET` | `/api/history/{node_id}` | Recent sensor readings for a node |
| `GET` | `/api/risk` | All risk assessments |
| `GET` | `/api/risk/{node_id}` | Risk assessment history for one node |
| `GET` | `/api/device-health/{node_id}` | Device-condition signals from the latest reading |
| `GET` | `/api/alerts` | Active HIGH/CRITICAL risk assessments |
| `GET` | `/api/observations/{node_id}` | Camera observations (snapshots + detection flags) for a node |
| `POST` | `/api/sensor-data` | Ingest a sensor reading from the ESP32; triggers a fresh risk computation |
| `POST` | `/api/image` | Ingest a camera snapshot + detection flags from the Pi; triggers a fresh risk computation |
| `POST` | `/api/ai-explanation/{node_id}` | On-demand: ask Claude to explain the current risk state in plain language |

Uploaded images are served statically at `/uploads/<filename>`.

## Risk engine

Risk is computed per-node, per-reading, using rolling z-score baselines against recent sensor history rather than fixed thresholds — so "risky" is relative to that node's own recent normal, not a hardcoded number. Assessments are classified into five tiers (exact thresholds live in `risk_engine.py`'s config) and factor in:

- Temperature and humidity rate of change
- Distance/structural shift rate of change
- Device health (ESP32 online status, sensor health, network status)
- Camera detections (currently: person presence)

Each new sensor reading *or* camera observation immediately triggers a recomputed assessment for that node — risk isn't batch-processed on a timer.

## Environment variables

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `BACKEND_URL` | Pi, ESP32 | `http://localhost:8000` | Where to POST sensor/image data |
| `NODE_ID` | Pi | `ARGUS-01` | Identifies this node's uploads |
| `ARGUS_UPLOAD_DIR` | Backend | `uploads` | Where camera snapshots are persisted on disk |
| `ANTHROPIC_API_KEY` | Backend | — | Enables `/api/ai-explanation/{node_id}` |
| `VITE_BACKEND_URL` | Dashboard | `http://localhost:8000` | Where the dashboard fetches data from |

## Known limitations

- **Smoke, water, and debris detection are not implemented.** YOLOv8n is trained on COCO, which has no classes for any of these. The `/api/image` endpoint currently sends `smoke`, `water`, and `debris` as `False` on every upload as a placeholder. Real detection for these would need either a custom-trained model or a different detection approach.
- **Single-camera-frame filename collisions across nodes** — resolved by keying uploaded filenames with `NODE_ID`, but worth double-checking if you add more nodes.
- **No authentication** on the backend API — fine for a local hackathon demo, not for anything exposed publicly. CORS is currently wide open (`allow_origins=["*"]`).
- **AI explanations are on-demand only**, not run automatically on every reading, to avoid unnecessary LLM calls (~every 2 seconds would be both slow and expensive).

## Roadmap

- [ ] Custom-trained detection for smoke/water/debris
- [ ] Multi-node dashboard map view
- [ ] Authenticated API access
- [ ] Historical trend charts per node
