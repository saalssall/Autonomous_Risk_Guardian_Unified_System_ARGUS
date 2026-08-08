import random
import random
import time
from database import insert_sensor_telemetry

NODES = ["ARGUS-01", "ARGUS-02", "ARGUS-03", "ARGUS-04"]

def simulate_node_data():
    print("Starting ARGUS Node Simulation Loop... Press Ctrl+C to stop.")
    while True:
        for node_id in NODES:
            temperature = round(random.uniform(22.0, 38.0), 2)
            humidity = round(random.uniform(30.0, 90.0), 2)
            distance = round(random.uniform(5.0, 100.0), 2)
            
            payload = {
                "node_id": node_id,
                "temperature": temperature,
                "humidity": humidity,
                "distance": distance,
                "device_health": {
                    "esp32": 1,
                    "dht11": 1,
                    "hc_sr04": 1,
                    "ir_beam": 1,
                    "network": 1
                },
                "status": "abnormal" if temperature > 32 or distance < 20 else "normal"
            }
            
            try:
                insert_sensor_telemetry(payload)
                print(f"[{time.strftime('%H:%M:%S')}] Ingested telemetry for {node_id}: Temp={temperature}C, Dist={distance}cm")
            except Exception as e:
                print(f"Error inserting simulation data for {node_id}: {e}")
                
        time.sleep(10)

if __name__ == "__main__":
    simulate_node_data()
