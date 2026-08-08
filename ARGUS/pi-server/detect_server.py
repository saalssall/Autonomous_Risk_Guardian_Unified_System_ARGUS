"""Authenticated ARGUS camera, detection, and sensor relay server.

Set ARGUS_ACCESS_TOKEN before starting. Never expose this service directly to
the internet: place it behind a TLS reverse proxy for production (wss/https).
"""
import asyncio
import hmac
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import websockets
from aiohttp import web
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("argus")

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
DASHBOARD_TOKEN = os.getenv("ARGUS_DASHBOARD_TOKEN", "")
SENSOR_TOKEN = os.getenv("ARGUS_SENSOR_TOKEN", "")
ALLOWED_ORIGINS = {origin.strip() for origin in os.getenv("ARGUS_ALLOWED_ORIGINS", "").split(",") if origin.strip()}
CONFIDENCE_THRESHOLD = 0.5
SCENE_CHANGE_THRESHOLD = float(os.getenv("SCENE_CHANGE_THRESHOLD", "0.12"))
MAX_MESSAGE_BYTES = 8192
MAX_STREAM_CLIENTS = 4

if min(len(DASHBOARD_TOKEN), len(SENSOR_TOKEN)) < 24:
    raise RuntimeError("Set unique ARGUS_DASHBOARD_TOKEN and ARGUS_SENSOR_TOKEN values of at least 24 characters.")

executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="argus")
model = YOLO("yolov8n.pt")
clients = set()
latest_jpeg_frame = None
frame_lock = asyncio.Lock()
stream_slots = asyncio.Semaphore(MAX_STREAM_CLIENTS)
scene_baseline = None


def token_is_valid(value, expected):
    return isinstance(value, str) and hmac.compare_digest(value, expected)


def valid_sensor(data):
    """Allow only bounded, expected sensor records to be relayed."""
    if not isinstance(data, dict) or data.get("type") != "sensor":
        return False
    node_id = data.get("node_id")
    if not isinstance(node_id, str) or not 1 <= len(node_id) <= 64:
        return False
    for field in ("temperature", "humidity", "distance_cm", "sound_level", "battery"):
        if field in data and (not isinstance(data[field], (int, float)) or not -10000 <= data[field] <= 100000):
            return False
    return True


async def authenticate(websocket):
    try:
        raw = await asyncio.wait_for(websocket.recv(), timeout=5)
        if not isinstance(raw, str) or len(raw.encode()) > MAX_MESSAGE_BYTES:
            return False
        message = json.loads(raw)
        if not isinstance(message, dict) or message.get("type") != "auth":
            return None
        if message.get("role") == "dashboard" and token_is_valid(message.get("token"), DASHBOARD_TOKEN):
            return "dashboard"
        if message.get("role") == "sensor" and token_is_valid(message.get("token"), SENSOR_TOKEN):
            return "sensor"
        return None
    except (asyncio.TimeoutError, json.JSONDecodeError, websockets.ConnectionClosed):
        return False


async def broadcast(message, exclude=None):
    payload = json.dumps(message, separators=(",", ":"))
    targets = [client for client in clients if client is not exclude]
    results = await asyncio.gather(*(client.send(payload) for client in targets), return_exceptions=True)
    for client, result in zip(targets, results):
        if isinstance(result, Exception):
            clients.discard(client)


async def handle_ws_client(websocket):
    role = await authenticate(websocket)
    if not role:
        await websocket.close(code=1008, reason="Authentication required")
        return
    if role == "dashboard":
        clients.add(websocket)
    await websocket.send(json.dumps({"type": "auth_ok", "role": role}))
    log.info("Authenticated %s connected (%d dashboard clients)", role, len(clients))
    try:
        async for raw in websocket:
            if not isinstance(raw, str) or len(raw.encode()) > MAX_MESSAGE_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                return
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if role == "sensor" and valid_sensor(data):
                await broadcast(data, exclude=websocket)
    finally:
        clients.discard(websocket)


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    return cap if cap.isOpened() else None


def encode_jpeg(frame):
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buffer.tobytes() if ok else None


def analyse_visual_frame(frame):
    """Run supported visual signals in a worker thread.

    YOLO supplies person count. Scene change is a deliberately simple frame
    comparison against a slowly adapting baseline; it is an observation, not
    a hazard classifier.
    """
    global scene_baseline
    results = model(frame, verbose=False)[0]
    people = []
    for box in results.boxes:
        if model.names[int(box.cls)] == "person" and float(box.conf) >= CONFIDENCE_THRESHOLD:
            people.append(float(box.conf))

    gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY).astype("float32")
    if scene_baseline is None:
        scene_baseline = gray
        change_score = 0.0
    else:
        change_score = min(1.0, float(cv2.absdiff(gray, scene_baseline).mean() / 255.0))
        # Adapt slowly so persistent lighting changes do not remain alerts forever.
        cv2.accumulateWeighted(gray, scene_baseline, 0.03)
    return people, change_score


async def capture_loop():
    global latest_jpeg_frame
    loop = asyncio.get_running_loop()
    cap = None
    frame_count = 0
    while True:
        if cap is None:
            cap = await loop.run_in_executor(executor, open_camera)
            if cap is None:
                log.warning("Camera unavailable; retrying in 2 seconds")
                await asyncio.sleep(2)
                continue
        ok, frame = await loop.run_in_executor(executor, cap.read)
        if not ok:
            cap.release()
            cap = None
            continue
        jpeg = await loop.run_in_executor(executor, encode_jpeg, frame)
        if jpeg:
            async with frame_lock:
                latest_jpeg_frame = jpeg
        frame_count += 1
        if frame_count % 5 == 0:
            people, change_score = await loop.run_in_executor(executor, analyse_visual_frame, frame)
            timestamp = int(time.time() * 1000)
            await broadcast({
                "type": "visual_observation",
                "people_count": len(people),
                "scene_change": round(change_score, 3),
                "timestamp": timestamp,
            })
            for confidence in people:
                await broadcast({"type": "detection", "label": "person", "confidence": confidence, "timestamp": timestamp})
            if change_score >= SCENE_CHANGE_THRESHOLD:
                await broadcast({"type": "detection", "label": "scene_change", "confidence": change_score, "timestamp": timestamp})
        await asyncio.sleep(0)


async def mjpeg_stream_handler(request):
    if not token_is_valid(request.query.get("token"), DASHBOARD_TOKEN):
        raise web.HTTPUnauthorized(text="Authentication required")
    if stream_slots.locked() and getattr(stream_slots, "_value", 0) <= 0:
        raise web.HTTPServiceUnavailable(text="Stream capacity reached")
    async with stream_slots:
        response = web.StreamResponse(status=200, headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
        await response.prepare(request)
        try:
            while True:
                async with frame_lock:
                    frame = latest_jpeg_frame
                if frame:
                    await response.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                await asyncio.sleep(1 / 15)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        return response


async def main():
    app = web.Application()
    app.router.add_get("/stream", mjpeg_stream_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", HTTP_PORT).start()
    log.info("Authenticated MJPEG service listening on port %d", HTTP_PORT)
    # ESP32 clients do not normally send an Origin header; they still must authenticate.
    origin_policy = (ALLOWED_ORIGINS | {None}) if ALLOWED_ORIGINS else None
    async with websockets.serve(handle_ws_client, "0.0.0.0", WEBSOCKET_PORT, origins=origin_policy, max_size=MAX_MESSAGE_BYTES, compression=None):
        log.info("Authenticated WebSocket service listening on port %d", WEBSOCKET_PORT)
        await capture_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down")
