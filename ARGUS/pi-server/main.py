from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
from database import (
    insert_sensor_telemetry,
    get_latest_telemetry,
    get_node_history,
    get_all_active_nodes
)
from sensor_fusion import (
    calculate_device_health,
    get_health_status,
    calculate_risk_score,
    calculate_confidence,
    calculate_spatial_agreement,
    calculate_historical_similarity,
    calculate_risk_trend,
    get_risk_category
)

app = FastAPI(title="ARGUS API", version="1.0.0")

class DeviceHealthSchema(BaseModel):
    esp32: int = 1
    dht11: int = 1
    hc_sr04: int = 1
    ir_beam: int = 1
    network: int = 1

class TelemetryPayload(BaseModel):
    node_id: str
    temperature: float
    humidity: float
    distance: float
    device_health: DeviceHealthSchema
    status: Optional[str] = "normal"

@app.post("/api/sensor-data")
def post_sensor_data(payload: TelemetryPayload):
    try:
        data = payload.dict()
        insert_sensor_telemetry(data)
        return {"status": "success", "message": f"Telemetry recorded for {payload.node_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/nodes")
def get_nodes():
    nodes = get_all_active_nodes()
    return {"nodes": nodes}

@app.get("/api/risk/{node_id}")
def get_node_risk(node_id: str, profile: str = Query("default", enum=["default", "flood", "heat"])):
    latest = get_latest_telemetry(node_id)
    if not latest:
        raise HTTPException(status_code=404, detail="Node data not found")
    
    history = get_node_history(node_id, limit=10)
    all_nodes = get_all_active_nodes()
    
    statuses = [n.get("status", "normal") for n in all_nodes if n.get("node_id") != node_id]
    spatial_score = calculate_spatial_agreement(statuses)
    
    current_vec = [latest["temperature"], latest["humidity"], latest["distance"]]
    hist_vec = [history[0]["temperature"], history[0]["humidity"], history[0]["distance"]] if history else current_vec
    hist_similarity = calculate_historical_similarity(current_vec, hist_vec)
    
    anomalies = {
        "temperature": min(max((latest["temperature"] - 20) / 20, 0), 1),
        "humidity": min(max(latest["humidity"] / 100, 0), 1),
        "distance": min(max((100 - latest["distance"]) / 100, 0), 1),
        "spatial_agreement": spatial_score,
        "historical_similarity": hist_similarity,
        "rate_of_change": 0.5
    }
    
    risk_score = calculate_risk_score(anomalies, profile=profile)
    risk_cat = get_risk_category(risk_score)
    
    health_score = calculate_device_health(latest.get("device_health", {}))
    cd = health_score / 100.0
    adjusted_risk = round(risk_score * cd, 2)
    
    confidence = calculate_confidence(
        c_sensor=0.9, 
        c_spatial=spatial_score, 
        c_history=hist_similarity, 
        c_device=cd
    )
    
    recent_risks = [risk_score * 0.9, risk_score * 0.95, risk_score]
    trend = calculate_risk_trend(recent_risks, [1, 1, 1])

    return {
        "node_id": node_id,
        "profile": profile,
        "risk_score": adjusted_risk,
        "raw_risk_score": risk_score,
        "risk_category": risk_cat,
        "confidence_percentage": confidence,
        "trend": trend,
        "device_health_score": health_score
    }

@app.get("/api/history/{node_id}")
def get_history(node_id: str, limit: int = 50):
    history = get_node_history(node_id, limit=limit)
    return {"node_id": node_id, "history": history}

@app.get("/api/device-health/{node_id}")
def get_device_health(node_id: str):
    latest = get_latest_telemetry(node_id)
    if not latest:
        raise HTTPException(status_code=404, detail="Node data not found")
        
    health_metrics = latest.get("device_health", {})
    score = calculate_device_health(health_metrics)
    status = get_health_status(score)
    
    return {
        "node_id": node_id,
        "health_score": score,
        "health_status": status,
        "components": health_metrics
    }

@app.get("/api/alerts")
def get_alerts():
    nodes = get_all_active_nodes()
    alerts = []
    for node in nodes:
        temp = node.get("temperature", 0)
        if temp > 32:
            alerts.append({
                "node_id": node["node_id"],
                "severity": "HIGH",
                "message": f"Node {node['node_id']} reporting high temperature threshold: {temp}°C"
            })
    return {"alerts": alerts}
