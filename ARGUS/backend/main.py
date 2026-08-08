from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import shutil
import os
import datetime
import database

app = FastAPI(title="Argus Disaster Recovery API", version="1.0")

# Ensure upload directory exists for camera images
UPLOAD_DIR = "uploads"
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


def _touch_node(db: Session, node_id: str, latitude, longitude):
    """ADDED: upsert a NodeModel row so a sensor/image post from a node that
    hasn't been manually seeded doesn't leave a dangling foreign key, and so
    /api/nodes reflects reality without needing seed.py to be run first.
    Doesn't overwrite status/battery on an existing row — those are set
    elsewhere (or default) and this only fills them in for a brand-new node.
    """
    node = db.query(database.NodeModel).filter(database.NodeModel.node_id == node_id).first()
    if node is None:
        db.add(database.NodeModel(
            node_id=node_id,
            latitude=latitude or 0.0,
            longitude=longitude or 0.0,
            status="HEALTHY",
            battery=100,
        ))
    else:
        node.last_seen = datetime.datetime.utcnow()


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
    db: Session = Depends(get_db)
):
    _touch_node(db, node_id, latitude, longitude)  # ADDED

    reading = database.SensorReadingModel(
        node_id=node_id,
        temperature=temperature,
        humidity=humidity,
        distance=distance,
        sound=sound,
        beam_status=beam_status,
        latitude=latitude,
        longitude=longitude
    )
    db.add(reading)
    db.commit()
    return {"status": "success", "message": "Sensor telemetry recorded."}


@app.post("/api/image")
def ingest_image(
    node_id: str = Form(...),
    file: UploadFile = File(...),
    smoke: bool = Form(False),
    water: bool = Form(False),
    person: bool = Form(False),
    debris: bool = Form(False),
    confidence: float = Form(...),
    db: Session = Depends(get_db)
):
    """Receives camera uploads and vision detections from pipeline teammates."""
    _touch_node(db, node_id, None, None)  # ADDED

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
    return {"status": "success", "message": "Camera observation and image logged successfully."}
