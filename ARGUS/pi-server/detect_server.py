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
from picamera2 import Picamera2
from ultralytics import YOLO

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
NODE_ID = os.environ.get("NODE_ID", "ARGUS-01")
NODE_LATITUDE = os.environ.get("NODE_LATITUDE")    # e.g. "37.7749"
NODE_LONGITUDE = os.environ.get("NODE_LONGITUDE")  # e.g. "-122.4194"
UPLOAD_INTERVAL_S = 5  # how often to send a snapshot — every frame would overload the backend
CONFIDENCE_THRESHOLD = 0.5

model = YOLO("yolov8n.pt")  # pretrained on COCO — downloads automatically on first run


def capture_and_upload(cap):
    # CHANGED: the official Pi Camera Module runs on the libcamera stack,
    # which cv2.VideoCapture doesn't support (it only talks V4L2, and hangs
    # with a "select() timeout" against this camera). Picamera2 captures
    # directly to a numpy array in RGB order — convert to BGR and everything
    # below (YOLO, cv2.imencode, upload) is unchanged.
    frame_rgb = cap.capture_array()
    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

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

    # FIXED: filename now includes NODE_ID. The backend saves uploads as
    # os.path.join(UPLOAD_DIR, file.filename) — a hardcoded "snapshot.jpg"
    # meant every node overwrote the same file on disk, so with more than
    # one node running, GET /api/observations/{node_id} for node B could
    # end up pointing at node A's photo. Keying the filename by node_id
    # keeps each node's image separate.
    files = {"file": (f"{NODE_ID}_snapshot.jpg", buffer.tobytes(), "image/jpeg")}
    data = {
        "node_id": NODE_ID,
        "smoke": False,   # not implemented — see module docstring
        "water": False,   # not implemented — see module docstring
        "person": person_detected,
        "debris": False,  # not implemented — see module docstring
        "confidence": confidence,
    }
    # ADDED: without real coordinates, the backend defaults any brand-new
    # node to (0.0, 0.0) — "Null Island" — which puts it nowhere near your
    # other seeded nodes on the map. Only sent if the env vars are set, so
    # an already-seeded node's real coordinates aren't overwritten.
    if NODE_LATITUDE is not None:
        data["latitude"] = NODE_LATITUDE
    if NODE_LONGITUDE is not None:
        data["longitude"] = NODE_LONGITUDE
    try:
        response = requests.post(f"{BACKEND_URL}/api/image", data=data, files=files, timeout=10)
        print(f"POST /api/image -> {response.status_code}")
    except requests.RequestException as error:
        print(f"Upload failed: {error}")


def main():
    cap = Picamera2()
    # A 640x480 preview-quality config is plenty for YOLOv8n + a JPEG
    # snapshot upload, and keeps capture fast on Pi-class CPUs.
    config = cap.create_preview_configuration(main={"size": (640, 480)})
    cap.configure(config)
    cap.start()
    time.sleep(2)  # let auto-exposure/white-balance settle before the first capture

    try:
        while True:
            capture_and_upload(cap)
            time.sleep(UPLOAD_INTERVAL_S)
    finally:
        cap.stop()


if __name__ == "__main__":
    main()