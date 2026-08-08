"""
Runs on the rover. Captures camera frames, detects people with a pretrained
YOLOv8n model, and broadcasts each detection to any connected dashboard over
WebSocket — matching the { label, confidence, timestamp } shape the React
dashboard's useWebSocket hook expects.

Install: pip install ultralytics opencv-python websockets
Run:     python detect_server.py
"""

import asyncio
import json
import time

import cv2
import websockets
from ultralytics import YOLO

MODEL = YOLO("yolov8n.pt")  # pretrained on COCO — downloads automatically on first run
CONFIDENCE_THRESHOLD = 0.5
DETECT_EVERY_N_FRAMES = 5  # skip frames so a Pi's CPU can keep up

connected_clients = set()


async def handle_client(websocket):
    # Every connection — the dashboard OR the ESP32 — lands here. The ESP32
    # connects as a plain WebSocket client and sends its own sensor JSON;
    # anything it sends gets relayed straight through to everyone else
    # (the dashboard). This is the whole "backend": no separate server needed.
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            await broadcast(message, exclude=websocket)
    finally:
        connected_clients.discard(websocket)


async def broadcast(message, exclude=None):
    if not connected_clients:
        return  # nobody connected yet — nothing to send
    payload = message if isinstance(message, str) else json.dumps(message)
    targets = [c for c in connected_clients if c is not exclude]
    await asyncio.gather(
        *(client.send(payload) for client in targets),
        return_exceptions=True,  # a dropped client shouldn't crash the loop
    )


async def detection_loop():
    capture = cv2.VideoCapture(0)
    frame_count = 0

    while True:
        ok, frame = capture.read()
        if not ok:
            await asyncio.sleep(0.1)
            continue

        frame_count += 1
        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            results = MODEL(frame, verbose=False)[0]
            for box in results.boxes:
                label = MODEL.names[int(box.cls)]
                confidence = float(box.conf)
                if label == "person" and confidence >= CONFIDENCE_THRESHOLD:
                    await broadcast(
                        {
                            "type": "detection",
                            "label": label,
                            "confidence": confidence,
                            "timestamp": time.time() * 1000,  # ms — matches JS `new Date()`
                        }
                    )

        await asyncio.sleep(0.01)  # yield so the WebSocket server can serve clients


async def main():
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        await detection_loop()


if __name__ == "__main__":
    asyncio.run(main())
