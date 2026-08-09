from fastapi import FastAPI
from pydantic import BaseModel
from database import init_db, fetch_latest_telemetry, insert_telemetry
from sensor_fusion import evaluate_device_health

app = FastAPI(title="Argus Telemetry & Sensor Fusion API")

@app.on_event("startup") 
def startup_event():
    init_db()

class TelemetryPayload(BaseModel):
    node_id: str
    temperature: float
    humidity: float
    distance: float
    spatial_agreement: float = 100.0

@app.get("/")
def read_root():
    return {"project": "Argus Telemetry System", "status": "Active"}

@app.get("/telemetry")
def get_telemetry(limit: int = 20):
    return {"data": fetch_latest_telemetry(limit)}

@app.post("/telemetry")
def post_telemetry(payload: TelemetryPayload):
    health_components, health_pct, status = evaluate_device_health(
        payload.temperature, payload.humidity, payload.distance
    )
    
    insert_telemetry(
        node_id=payload.node_id,
        temperature=payload.temperature,
        humidity=payload.humidity,
        distance=payload.distance,
        device_health=health_components,
        health_percentage=health_pct,
        spatial_agreement=payload.spatial_agreement,
        status=status.lower()
    )
    
    return {
        "status": "success",
        "evaluated_status": status,
        "device_health_percentage": f"{health_pct}%",
        "device_health_details": health_components
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
