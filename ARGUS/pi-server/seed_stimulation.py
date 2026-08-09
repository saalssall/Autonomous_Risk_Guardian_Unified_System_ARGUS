import time
import random
from database import insert_telemetry, init_db
from sensor_fusion import evaluate_device_health, calculate_spatial_correlation

NODES = ["ARGUS-01", "ARGUS-02", "ARGUS-03", "ARGUS-04"]

def run_simulation(iterations=5, delay=1):
    init_db()
    print("Starting Argus Telemetry Simulation with Expanded Health & Spatial Correlation...")
    
    for _ in range(iterations):
        node_risks = {}
        node_data_buffer = {}
        
        for node in NODES:
            temp = round(random.uniform(20.0, 45.0), 2)
            humidity = round(random.uniform(30.0, 85.0), 2)
            distance = round(random.uniform(5.0, 150.0), 2)
            
            health, health_pct, status = evaluate_device_health(temp, humidity, distance)
            
            risk_level = "HIGH" if temp > 40 or health_pct < 60 else ("ELEVATED" if temp > 32 else "LOW")
            node_risks[node] = risk_level
            node_data_buffer[node] = {
                "temp": temp, "hum": humidity, "dist": distance, 
                "health": health, "health_pct": health_pct, "status": status
            }

        spatial_agreement = calculate_spatial_correlation(node_risks)

        for node, data in node_data_buffer.items():
            insert_telemetry(
                node_id=node,
                temperature=data["temp"],
                humidity=data["hum"],
                distance=data["dist"],
                device_health=data["health"],
                health_percentage=data["health_pct"],
                spatial_agreement=spatial_agreement,
                status=data["status"].lower()
            )
            print(f"Logged [{data['status']}] {node} -> Health: {data['health_pct']}% | Spatial Agreement: {spatial_agreement}%")
            
        time.sleep(delay)

if __name__ == "__main__":
    run_simulation(iterations=3, delay=0.5)
