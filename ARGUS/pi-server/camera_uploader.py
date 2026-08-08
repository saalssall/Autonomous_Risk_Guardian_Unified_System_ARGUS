"""
Runs on the Raspberry Pi. Captures camera frames, runs YOLOv8n for person
detection, and periodically POSTs a snapshot + detection flags to the
FastAPI backend's /api/image endpoint.

IMPORTANT: smoke, water, and debris detection are NOT implemented — YOLOv8n
is trained on COCO, which has no classes for any of these. They're sent as
False on every upload as a placeholder. If real detection for these matters
for the demo, it needs either a custom-trained model or a different
detection approach — out of scope to add here without a decision on which.
"""
import os
import time

import cv2
import requests
from ultralytics import YOLO

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
NODE_ID = os.environ.get("NODE_ID", "ARGUS-01")
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
UPLOAD_INTERVAL_S = 5  # how often to send a snapshot — every frame would overload the backend
CONFIDENCE_THRESHOLD = 0.5

model = YOLO("yolov8n.pt")  # pretrained on COCO — downloads automatically on first run


def capture_and_upload(cap):
    ok, frame = cap.read()
    if not ok:
        print("Camera read failed")
        return

    results = model(frame, verbose=False)[0]
    person_confidences = [
        float(box.conf) for box in results.boxes
        if model.names[int(box.cls)] == "person" and float(box.conf) >= CONFIDENCE_THRESHOLD
    ]
    person_detected = len(person_confidences) > 0
    confidence = max(person_confidences, default=0.0)

    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok:
        print("JPEG encode failed")
        return

    files = {"file": ("snapshot.jpg", buffer.tobytes(), "image/jpeg")}
    data = {
        "node_id": NODE_ID,
        "smoke": False,   # not implemented — see module docstring
        "water": False,   # not implemented — see module docstring
        "person": person_detected,
        "debris": False,  # not implemented — see module docstring
        "confidence": confidence,
    }
    try:
        response = requests.post(f"{BACKEND_URL}/api/image", data=data, files=files, timeout=10)
        print(f"POST /api/image -> {response.status_code}")
    except requests.RequestException as error:
        print(f"Upload failed: {error}")


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    while True:
        capture_and_upload(cap)
        time.sleep(UPLOAD_INTERVAL_S)


if __name__ == "__main__":
    main()
