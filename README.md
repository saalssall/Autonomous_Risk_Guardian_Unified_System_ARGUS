# Disaster recovery sensor node

Four pieces. ESP32 and the camera pipeline both POST data to the backend;
the dashboard polls the backend over REST (no WebSocket in this version).

```
backend/              FastAPI + SQLite — stores everything, serves it back over REST
dashboard/             React app (Vite) — polls the backend, shows the operator UI
pi-server/             Python — camera_uploader.py posts snapshots to the backend
esp32-sensor-node/     PlatformIO project — ESP32 firmware POSTs sensor readings
```

`pi-server/server.py`, `detect_server.py`, and `mock_sensor.py` are from an
earlier WebSocket-based architecture and are no longer used by anything else
here — kept in case they're wanted as a fallback, otherwise safe to delete.

## Running everything

Open `disaster-recovery.code-workspace` in VS Code — shows all folders in
one window without merging their configs.

**backend** (run this first):
```
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**dashboard**:
```
cd dashboard
npm install
npm run dev
```
Connect it to `http://localhost:8000` with node ID `ARGUS-01` (or whatever
node ID the ESP32/camera pipeline are using — they must all match).

**pi-server** (camera pipeline):
```
cd pi-server
pip install -r requirements.txt
python3 camera_uploader.py
```

**esp32-sensor-node**:
Open the folder in PlatformIO, fill in Wi-Fi credentials and `BACKEND_HOST`
in `src/main.cpp`, then build + upload.
