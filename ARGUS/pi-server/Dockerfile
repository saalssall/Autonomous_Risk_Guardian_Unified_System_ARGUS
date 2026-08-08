# Build and run from pi-server/ directly:
#   docker build -t argus-camera .
#
# IMPORTANT — camera access:
# On Linux (including the Raspberry Pi itself), run with device passthrough:
#   docker run --device=/dev/video0 -e BACKEND_URL=http://<backend-host>:8000 argus-camera
# On macOS/Windows, Docker Desktop runs containers inside a Linux VM with no
# path to the host's webcam — there is no equivalent of --device=/dev/video0
# that works there. A container built from this Dockerfile will NOT be able
# to see your Mac's camera. For local testing on a Mac, keep running
# camera_uploader.py directly (as before) — use this image specifically when
# deploying to the actual Raspberry Pi.
FROM python:3.11-slim

WORKDIR /app

# opencv-python needs these even though they're not Python packages — the
# slim base image doesn't include them, and cv2 fails to import without them.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV BACKEND_URL=http://localhost:8000
ENV NODE_ID=ARGUS-01
CMD ["python3", "camera_uploader.py"]
