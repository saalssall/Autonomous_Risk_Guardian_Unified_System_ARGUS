import math
import numpy as np

def calculate_device_health(health_metrics: dict) -> float:
    e = health_metrics.get("esp32", 1)
    d = health_metrics.get("dht11", 1)
    u = health_metrics.get("hc_sr04", 1)
    i = health_metrics.get("ir_beam", 1)
    n = health_metrics.get("network", 1)
    
    score = 100 * (0.30 * e + 0.20 * d + 0.20 * u + 0.20 * i + 0.10 * n)
    return round(score, 2)

def get_health_status(health_score: float) -> str:
    if health_score >= 90:
        return "HEALTHY"
    elif health_score >= 70:
        return "DEGRADED"
    elif health_score >= 40:
        return "COMPROMISED"
    else:
        return "OFFLINE / FAILED"

def calculate_risk_score(anomalies: dict, profile: str = "default") -> float:
    at = anomalies.get("temperature", 0.0)
    ah = anomalies.get("humidity", 0.0)
    ad = anomalies.get("distance", 0.0)
    as_spatial = anomalies.get("spatial_agreement", 0.0)
    ahist = anomalies.get("historical_similarity", 0.0)
    arate = anomalies.get("rate_of_change", 0.0)

    if profile == "flood":
        weights = {"T": 0.10, "H": 0.15, "D": 0.40, "Rate": 0.15, "Spatial": 0.10, "Hist": 0.10}
    elif profile == "heat":
        weights = {"T": 0.40, "H": 0.20, "D": 0.05, "Rate": 0.15, "Spatial": 0.10, "Hist": 0.10}
    else:
        weights = {"T": 0.25, "H": 0.15, "D": 0.25, "Rate": 0.15, "Spatial": 0.10, "Hist": 0.10}

    raw_risk = 100 * (
        weights["T"] * at +
        weights["H"] * ah +
        weights["D"] * ad +
        weights["Rate"] * arate +
        weights["Spatial"] * as_spatial +
        weights["Hist"] * ahist
    )
    return round(min(max(raw_risk, 0), 100), 2)

def calculate_confidence(c_sensor: float, c_spatial: float, c_history: float, c_device: float) -> float:
    c = 0.4 * c_sensor + 0.25 * c_spatial + 0.20 * c_history + 0.15 * c_device
    return round(c * 100, 2)

def calculate_spatial_agreement(nearby_nodes_status: list) -> float:
    if not nearby_nodes_status:
        return 1.0
    abnormal_count = sum(1 for status in nearby_nodes_status if status == "abnormal")
    return round(abnormal_count / len(nearby_nodes_status), 2)

def calculate_historical_similarity(current_vector: list, historical_vector: list) -> float:
    curr = np.array(current_vector)
    hist = np.array(historical_vector)
    d = np.linalg.norm(curr - hist)
    similarity = 1.0 / (1.0 + d)
    return round(float(similarity), 2)

def calculate_risk_trend(recent_risks: list, time_deltas: list) -> str:
    if len(recent_risks) < 2:
        return "STABLE"
    
    rt = recent_risks[-1]
    rt_k = recent_risks[0]
    delta_t = sum(time_deltas) if time_deltas else 1.0
    
    m = (rt - rt_k) / max(delta_t, 1.0)
    
    if m > 0.10:
        return "INCREASING"
    elif m < -0.10:
        return "DECREASING"
    else:
        return "STABLE"

def get_risk_category(score: float) -> str:
    if score < 20:
        return "LOW"
    elif score < 40:
        return "GUARDED"
    elif score < 60:
        return "ELEVATED"
    elif score < 80:
        return "HIGH"
    else:
        return "CRITICAL"

def evaluate_device_health(temperature, humidity, distance):
    """
    Evaluates individual component states matching the expanded checklist:
    - ESP32: ONLINE/OFFLINE
    - DHT11: OK/ERROR
    - HC-SR04: OK/ERROR
    - IR BEAM: INTACT/BROKEN
    - Raspberry Pi: ONLINE/OFFLINE
    - Camera: ONLINE/OFFLINE
    """
    health_components = {
        "esp32": "ONLINE",
        "dht11": "OK" if 0 <= temperature <= 50 and 20 <= humidity <= 90 else "ERROR",
        "hc_sr04": "OK" if distance >= 0 else "ERROR",
        "ir_beam": "INTACT" if distance > 10 else "BROKEN",
        "raspberry_pi": "ONLINE",
        "camera": "ONLINE"
    }
    
    total_components = len(health_components)
    operational_count = sum(
        1 for status in health_components.values() 
        if status in ["ONLINE", "OK", "INTACT"]
    )
    health_percentage = round((operational_count / total_components) * 100.0, 2)
    
    overall_status = "HEALTHY" if health_percentage >= 80 else "DEGRADED"
    if health_percentage < 50:
        overall_status = "CRITICAL"

    return health_components, health_percentage, overall_status

def calculate_spatial_correlation(all_node_risks):
    """
    Calculates spatial agreement ratio across nodes (e.g., 3/4 = 75%).
    all_node_risks: dict mapping node_id to risk level ("HIGH", "ELEVATED", "LOW")
    """
    if not all_node_risks:
        return 100.0
    
    total_nodes = len(all_node_risks)
    dominant_status = max(set(all_node_risks.values()), key=list(all_node_risks.values()).count)
    matching_nodes = sum(1 for status in all_node_risks.values() if status == dominant_status)
    
    spatial_agreement = round((matching_nodes / total_nodes) * 100.0, 2)
    return spatial_agreement
