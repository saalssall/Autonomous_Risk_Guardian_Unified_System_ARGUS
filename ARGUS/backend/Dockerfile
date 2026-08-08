# Build from the PROJECT ROOT, not from inside backend/ — this needs to
# reach argus_config.json, which lives one level above backend/:
#   docker build -f backend/Dockerfile -t argus-backend .
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# argus_config.json lives outside backend/ in the repo — bundled here at a
# fixed path so risk_engine.py doesn't depend on the container's directory
# structure matching the repo's. See the ARGUS_CONFIG_PATH env var below.
COPY argus_config.json /app/argus_config.json
ENV ARGUS_CONFIG_PATH=/app/argus_config.json

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
