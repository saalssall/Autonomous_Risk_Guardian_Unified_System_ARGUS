"""
ARGUS Pi server
----------------
Runs on the Raspberry Pi (or a dev laptop, for testing). Does three jobs:

  1. Captures camera frames and serves them as an MJPEG stream over HTTP,
     so the dashboard's CameraFeed component has a real feed to show —
     not just a WebSocket detection log with an empty video box.
  2. Runs YOLOv8n person-detection on a sampled subset of frames and
     broadcasts detections over WebSocket.
  3. Relays whatever the ESP32 sends (sensor JSON) straight through to
     any connected dashboard, unchanged.

Why this looks different from the first version: camera capture and YOLO
inference are both blocking, CPU-bound calls. Calling them directly inside
an asyncio coroutine freezes the ENTIRE event loop for the duration of each
call — including the WebSocket server, so sensor readings from the ESP32
would queue up and arrive in laggy bursts instead of streaming smoothly.
Both are now offloaded to a small thread pool so the event loop stays
responsive no matter how long inference takes.

Install: pip install ultralytics opencv-python websockets aiohttp
Run:     python3 detect_server.py
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import websockets
from aiohttp import web
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("argus")

# ---- Config — tune these once you know your target hardware's real performance ----
CAMERA_INDEX = 0
WEBSOCKET_PORT = 8765
HTTP_PORT = 8080
CONFIDENCE_THRESHOLD = 0.5
DETECT_EVERY_N_FRAMES = 5       # run YOLO on every Nth captured frame — keeps a Pi's CPU from choking
JPEG_QUALITY = 70                # 0-100, for the MJPEG stream; lower = faster/smaller, blurrier
STREAM_FPS_CAP = 15              # MJPEG output rate, independent of camera capture rate
CAMERA_RETRY_DELAY_S = 2

# Two workers: one for camera reads, one for YOLO inference, so they can
# overlap rather than fully serialize on a single thread.
executor = ThreadPoolExecutor(max_workers=2)
model = YOLO("yolov8n.pt")  # pretrained on COCO — downloads automatically on first run

connected_ws_clients = set()
latest_jpeg_frame = None  # shared between capture_loop() and the HTTP stream handler
frame_lock = asyncio.Lock()


# ---------- WebSocket: relay ESP32 sensor data + broadcast detections ----------

async def handle_ws_client(websocket):
    connected_ws_clients.add(websocket)
    log.info("Client connected (%d total)", len(connected_ws_clients))
    try:
        async for message in websocket:
            # Anything a client sends (the ESP32's sensor JSON) gets relayed
            # straight through to everyone else (the dashboard). No parsing
            # or validation here on purpose — keeps this server a dumb pipe
            # that can't itself corrupt the payload.
            await broadcast(message, exclude=websocket)
    except websockets.ConnectionClosed:
        pass  # normal on disconnect — nothing to log as an error
    finally:
        connected_ws_clients.discard(websocket)
        log.info("Client disconnected (%d total)", len(connected_ws_clients))


async def broadcast(message, exclude=None):
    if not connected_ws_clients:
        return
    payload = message if isinstance(message, str) else json.dumps(message)
    targets = [c for c in connected_ws_clients if c is not exclude]
    if not targets:
        return
    results = await asyncio.gather(
        *(client.send(payload) for client in targets),
        return_exceptions=True,  # one dropped client shouldn't crash the broadcast
    )
    for client, result in zip(targets, results):
        if isinstance(result, Exception):
            log.warning("Failed to send to a client: %s", result)


# ---------- Camera capture + inference — all blocking work stays off the event loop ----------

def open_camera():
    """Blocking — always call via executor."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    return cap if cap.isOpened() else None


def run_inference(frame):
    """Blocking — always call via executor."""
    return model(frame, verbose=False)[0]


def encode_jpeg(frame):
    """Blocking — always call via executor."""
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buffer.tobytes() if ok else None


async def capture_loop():
    global latest_jpeg_frame
    loop = asyncio.get_running_loop()

    cap = await loop.run_in_executor(executor, open_camera)
    while cap is None:
        log.error(
            "Camera not available at index %d — retrying in %ds. "
            "If this is a Pi Camera Module (CSI ribbon), cv2.VideoCapture may need "
            "a libcamera/GStreamer pipeline instead of a bare index.",
            CAMERA_INDEX, CAMERA_RETRY_DELAY_S,
        )
        await asyncio.sleep(CAMERA_RETRY_DELAY_S)
        cap = await loop.run_in_executor(executor, open_camera)
    log.info("Camera opened (index %d)", CAMERA_INDEX)

    frame_count = 0
    consecutive_failures = 0

    while True:
        ok, frame = await loop.run_in_executor(executor, cap.read)
        if not ok:
            consecutive_failures += 1
            if consecutive_failures % 20 == 1:  # don't spam the log every 100ms
                log.warning("Camera read failed (%d consecutive)", consecutive_failures)
            await asyncio.sleep(0.1)
            continue
        consecutive_failures = 0

        frame_count += 1

        jpeg_bytes = await loop.run_in_executor(executor, encode_jpeg, frame)
        if jpeg_bytes is not None:
            async with frame_lock:
                latest_jpeg_frame = jpeg_bytes

        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            results = await loop.run_in_executor(executor, run_inference, frame)
            for box in results.boxes:
                label = model.names[int(box.cls)]
                confidence = float(box.conf)
                if label == "person" and confidence >= CONFIDENCE_THRESHOLD:
                    await broadcast({
                        "type": "detection",
                        "label": label,
                        "confidence": confidence,
                        "timestamp": time.time() * 1000,  # ms — matches JS `new Date()`
                    })

        await asyncio.sleep(0)  # yield control back to the event loop between frames


# ---------- HTTP: MJPEG stream for the dashboard's CameraFeed component ----------

async def mjpeg_stream_handler(request):
    response = web.StreamResponse(
        status=200,
        headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"},
    )
    await response.prepare(request)
    try:
        while True:
            async with frame_lock:
                frame = latest_jpeg_frame
            if frame is not None:
                await response.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            await asyncio.sleep(1 / STREAM_FPS_CAP)
    except (ConnectionResetError, asyncio.CancelledError):
        pass  # client closed the <img> tag / navigated away — not an error
    return response


async def start_http_server():
    app = web.Application()
    app.router.add_get("/stream", mjpeg_stream_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    log.info("MJPEG stream serving at http://0.0.0.0:%d/stream", HTTP_PORT)


async def main():
    await start_http_server()
    async with websockets.serve(handle_ws_client, "0.0.0.0", WEBSOCKET_PORT):
        log.info("WebSocket server listening at ws://0.0.0.0:%d", WEBSOCKET_PORT)
        await capture_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down")