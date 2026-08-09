from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import shutil
import os
import datetime
import database
import risk_engine
import ai_explainer

load_dotenv()  # picks up .env in this folder, e.g. GEMINI_API_KEY — no-op if the file doesn't exist

app = FastAPI(title="Argus Disaster Recovery API", version="1.0")

# ADDED: the dashboard runs on a different origin (e.g. localhost:5173) than
# this backend (localhost:8000) — without CORS middleware, the browser
# silently blocks every fetch() call from it, which shows up as "Backend
# unreachable" even though the backend is running fine. allow_origins=["*"]
# is fine for a local demo; tighten it if this ever runs somewhere less trusted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists for camera images
# ADDED: configurable, same reasoning as DATA_DIR in database.py — otherwise
# a persisted database (via a volume) would end up with image_url rows
# pointing at files that vanish every time the container restarts.
UPLOAD_DIR = os.environ.get("ARGUS_UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ADDED: without this, image_url values stored in the DB (e.g. "uploads/x.jpg")
# were never reachable over HTTP — nothing in the original file served them.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

database.init_db()


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/nodes")
def get_nodes(db: Session = Depends(get_db)):
    return db.query(database.NodeModel).all()


@app.get("/api/nodes/{node_id}")
def get_node_detail(node_id: str, db: Session = Depends(get_db)):
    node = db.query(database.NodeModel).filter(database.NodeModel.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@app.get("/api/history/{node_id}")
def get_node_history(node_id: str, limit: int = 100, db: Session = Depends(get_db)):
    readings = db.query(database.SensorReadingModel)\
        .filter(database.SensorReadingModel.node_id == node_id)\
        .order_by(database.SensorReadingModel.timestamp.desc())\
        .limit(limit).all()
    return readings


@app.get("/api/risk")
def get_risk_assessments(db: Session = Depends(get_db)):
    return db.query(database.RiskAssessmentModel).all()


@app.get("/api/risk/{node_id}")
def get_node_risk(node_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """ADDED — the spec calls for this alongside GET /api/risk; risk
    assessments are now tied to a node_id so this can actually filter."""
    return db.query(database.RiskAssessmentModel)\
        .filter(database.RiskAssessmentModel.node_id == node_id)\
        .order_by(database.RiskAssessmentModel.timestamp.desc())\
        .limit(limit).all()


@app.get("/api/device-health/{node_id}")
def get_device_health(node_id: str, db: Session = Depends(get_db)):
    """ADDED. The spec lists this as a bare /api/device-health, but with
    multiple nodes that needs to be scoped to one — implemented per-node
    instead. Returns the device-condition fields from the most recent
    reading for this node."""
    latest = db.query(database.SensorReadingModel)\
        .filter(database.SensorReadingModel.node_id == node_id)\
        .order_by(database.SensorReadingModel.timestamp.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No readings for this node yet")
    return {
        "node_id": node_id,
        "timestamp": latest.timestamp,
        "esp32_online": latest.esp32_online,
        "dht11_status": latest.dht11_status,
        "hcsr04_status": latest.hcsr04_status,
        "ir_beam_status": latest.ir_beam_status,
        "network_status": latest.network_status,
    }


@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Returns active high or critical risk assessments for dashboard warning panels."""
    alerts = db.query(database.RiskAssessmentModel)\
        .filter(database.RiskAssessmentModel.risk_level.in_(["HIGH", "CRITICAL"]))\
        .order_by(database.RiskAssessmentModel.timestamp.desc()).all()
    return alerts


@app.get("/api/observations/{node_id}")
def get_node_observations(node_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """ADDED: there was no way to retrieve camera_observations via the API —
    only POST /api/image existed to create them. Mirrors get_node_history."""
    return db.query(database.CameraObservationModel)\
        .filter(database.CameraObservationModel.node_id == node_id)\
        .order_by(database.CameraObservationModel.timestamp.desc())\
        .limit(limit).all()


def _compute_node_status(esp32_online, dht11_status, hcsr04_status, ir_beam_status, network_status):
    """ADDED — buckets the 5 device-condition signals into a health score
    (0-100, 20 points each) and maps it to a status via the shared config's
    health_levels, instead of every node just defaulting to HEALTHY forever."""
    checks = [
        esp32_online is True,
        dht11_status == "OK",
        hcsr04_status == "OK",
        ir_beam_status == "OK",
        network_status == "CONNECTED",
    ]
    score = sum(20 for ok in checks if ok)
    for level, (low, high) in risk_engine.CONFIG["health_levels"].items():
        if low <= score <= high:
            return level
    return "OFFLINE"


def _touch_node(db: Session, node_id: str, latitude, longitude, status=None):
    """Upsert a NodeModel row so a sensor/image post from a node that hasn't
    been manually seeded doesn't leave a dangling foreign key, and so
    /api/nodes reflects reality without needing seed.py to be run first.
    """
    node = db.query(database.NodeModel).filter(database.NodeModel.node_id == node_id).first()
    if node is None:
        db.add(database.NodeModel(
            node_id=node_id,
            latitude=latitude or 0.0,
            longitude=longitude or 0.0,
            status=status or "HEALTHY",
            battery=100,
        ))
    else:
        node.last_seen = datetime.datetime.utcnow()
        if status is not None:
            node.status = status
        # ADDED: if real coordinates come in later for a node that was
        # first created with a 0.0/0.0 fallback (e.g. a sensor-data POST
        # arrived before an image POST with real lat/long), update it
        # rather than leaving it stuck at Null Island forever.
        if latitude is not None:
            node.latitude = latitude
        if longitude is not None:
            node.longitude = longitude


@app.post("/api/sensor-data")
def ingest_sensor_data(
    node_id: str = Form(...),
    temperature: float = Form(...),
    humidity: float = Form(...),
    distance: float = Form(...),
    sound: float = Form(None),
    beam_status: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    esp32_online: bool = Form(True),
    dht11_status: str = Form(None),
    hcsr04_status: str = Form(None),
    ir_beam_status: str = Form(None),
    network_status: str = Form(None),
    db: Session = Depends(get_db)
):
    node_status = _compute_node_status(esp32_online, dht11_status, hcsr04_status, ir_beam_status, network_status)
    _touch_node(db, node_id, latitude, longitude, status=node_status)

    reading = database.SensorReadingModel(
        node_id=node_id,
        temperature=temperature,
        humidity=humidity,
        distance=distance,
        sound=sound,
        beam_status=beam_status,
        latitude=latitude,
        longitude=longitude,
        esp32_online=esp32_online,
        dht11_status=dht11_status,
        hcsr04_status=hcsr04_status,
        ir_beam_status=ir_beam_status,
        network_status=network_status,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # ADDED — this is what makes risk real instead of hand-seeded: every
    # new reading immediately gets a fresh, computed assessment for its node.
    assessment = risk_engine.compute_risk_assessment(db, node_id, reading)

    return {
        "status": "success",
        "message": "Sensor telemetry recorded.",
        "risk_level": assessment.risk_level,
        "risk_score": assessment.risk_score,
    }


@app.post("/api/image")
def ingest_image(
    node_id: str = Form(...),
    file: UploadFile = File(...),
    smoke: bool = Form(False),
    water: bool = Form(False),
    person: bool = Form(False),
    debris: bool = Form(False),
    confidence: float = Form(...),
    latitude: float = Form(None),   # ADDED — see _touch_node call below
    longitude: float = Form(None),  # ADDED
    db: Session = Depends(get_db)
):
    """Receives camera uploads and vision detections from pipeline teammates."""
    # CHANGED: was _touch_node(db, node_id, None, None), which meant any
    # node first seen via an image upload (rather than seed.py) got created
    # at (0.0, 0.0) — Null Island — nowhere near the site's other nodes on
    # the map. Now accepts real coordinates from the Pi's upload if sent.
    _touch_node(db, node_id, latitude, longitude)

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    observation = database.CameraObservationModel(
        node_id=node_id,
        image_url=file_path,
        smoke=smoke,
        water=water,
        person=person,
        debris=debris,
        confidence=confidence
    )
    db.add(observation)
    db.commit()

    # ADDED — recompute risk against this node's latest sensor reading so a
    # camera detection (e.g. smoke) affects risk immediately, rather than
    # waiting for the next unrelated sensor-data POST to happen to trigger it.
    latest_reading = db.query(database.SensorReadingModel)\
        .filter(database.SensorReadingModel.node_id == node_id)\
        .order_by(database.SensorReadingModel.timestamp.desc()).first()
    if latest_reading:
        risk_engine.compute_risk_assessment(db, node_id, latest_reading)

    return {"status": "success", "message": "Camera observation and image logged successfully."}


def _build_ai_payload(db: Session, node_id: str):
    """Compact payload for the AI to interpret — current state + changes +
    risk + confidence + trend + device health, per the spec. Never includes
    raw sensor history or a long reading list."""
    assessment = db.query(database.RiskAssessmentModel)\
        .filter(database.RiskAssessmentModel.node_id == node_id)\
        .order_by(database.RiskAssessmentModel.timestamp.desc()).first()
    if assessment is None:
        return None

    readings = db.query(database.SensorReadingModel)\
        .filter(database.SensorReadingModel.node_id == node_id)\
        .order_by(database.SensorReadingModel.timestamp.desc())\
        .limit(risk_engine.BASELINE_WINDOW + 1).all()
    if not readings:
        return None
    latest = readings[0]
    oldest = readings[-1] if len(readings) > 1 else None

    def rate_str(current, oldest_value, unit):
        if oldest_value is None:
            return "no recent trend data"
        rate = risk_engine._real_rate_per_30min(current, oldest_value, latest.timestamp, oldest.timestamp)
        if rate is None:
            return "no recent trend data"
        sign = "+" if rate > 0 else ""
        return f"{sign}{rate:.1f}{unit} / 30min"

    device_health = _compute_node_status(
        latest.esp32_online, latest.dht11_status, latest.hcsr04_status,
        latest.ir_beam_status, latest.network_status,
    )

    return {
        "node": node_id,
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level,
        "confidence": assessment.confidence,
        "trend": assessment.trend,
        "temperature_change": rate_str(latest.temperature, oldest.temperature if oldest else None, "C"),
        "humidity_change": rate_str(latest.humidity, oldest.humidity if oldest else None, "%"),
        "distance_change": rate_str(latest.distance, oldest.distance if oldest else None, "cm"),
        "device_health": device_health,
    }


@app.post("/api/ai-explanation/{node_id}")
def get_ai_explanation(node_id: str, db: Session = Depends(get_db)):
    """ADDED — calls Gemini to interpret the already-computed risk
    assessment into a short human-readable explanation. Deliberately a
    separate, on-demand endpoint rather than wired into every sensor POST:
    calling an LLM on every ~2s reading would be slow and needlessly
    expensive. The dashboard should call this only when the user asks for it."""
    payload = _build_ai_payload(db, node_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="No data for this node yet")
    try:
        return ai_explainer.generate_ai_explanation(payload)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"AI explanation failed: {error}")