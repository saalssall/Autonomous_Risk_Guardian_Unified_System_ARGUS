from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import shutil
import os
import database

app = FastAPI(title="Argus Disaster Recovery API", version="1.0")

# Ensure upload directory exists for camera images
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
