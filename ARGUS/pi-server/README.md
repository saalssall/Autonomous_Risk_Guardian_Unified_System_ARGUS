# ARGUS Pi server

Runs on the Raspberry Pi. Does person detection and scene-change detection
on the camera feed, and relays sensor readings from the ESP32 — all over an
authenticated WebSocket. Also serves an authenticated MJPEG video stream.

## Setup

```
pip install -r requirements.txt
```

Set two required environment variables before starting — each must be a
unique random string, at least 24 characters:

```
export ARGUS_DASHBOARD_TOKEN="<random string>"
export ARGUS_SENSOR_TOKEN="<random string>"
```

Optional environment variables (defaults shown):

| Variable | Default | Purpose |
|---|---|---|
| `CAMERA_INDEX` | `0` | Which camera to open |
| `WEBSOCKET_PORT` | `8765` | WebSocket relay port |
| `HTTP_PORT` | `8080` | MJPEG stream port |
| `ARGUS_ALLOWED_ORIGINS` | (any) | Comma-separated allowed WebSocket origins |
| `SCENE_CHANGE_THRESHOLD` | `0.12` | Sensitivity for scene-change alerts |

## Running

```
python3 server.py
```

## Testing without real ESP32 hardware

`mock_sensor.py` simulates a sensor node: connects, authenticates, and sends
a fake reading every 2 seconds. After 60 seconds it starts simulating a
flood (distance drops, humidity rises) — useful for a demo.

```
export ARGUS_SENSOR_TOKEN="<same token as the server>"
python3 mock_sensor.py
```

## Connecting a client

Every WebSocket client — dashboard or sensor — must send an auth message
as the very first message, before anything else:

```json
{ "type": "auth", "role": "dashboard", "token": "<ARGUS_DASHBOARD_TOKEN>" }
```

The MJPEG stream also requires the dashboard token as a query parameter:
`http://<host>:8080/stream?token=<ARGUS_DASHBOARD_TOKEN>`
