# Disaster recovery sensor node

Three independent pieces, tied together by WebSocket at runtime — not by any shared code.

```
dashboard/           React app (Vite) — the operator UI
pi-server/           Python — runs on the Raspberry Pi, does YOLO detection + relays sensor data
esp32-sensor-node/   PlatformIO project — ESP32 firmware reading the sensors
```

## Running everything

Open `disaster-recovery.code-workspace` in VS Code — this shows all three folders
in one window without merging their configs (each keeps its own venv/node_modules/
PlatformIO settings).

**pi-server** (run this first):
```
cd pi-server
pip install -r requirements.txt
python3 detect_server.py
```

**dashboard**:
```
cd dashboard
npm install
npm run dev
```
Then connect it to `ws://localhost:8765` (or the Pi's IP once it's running there).

**esp32-sensor-node**:
Open the `esp32-sensor-node` folder in PlatformIO, fill in Wi-Fi credentials and
`PI_HOST` in `src/main.cpp`, then build + upload.
