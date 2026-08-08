"""
Simulates three additional ARGUS sensor nodes (ARGUS-02, ARGUS-03, ARGUS-04)
posting to the same POST /api/sensor-data endpoint, in the same format, as
the real ESP32 (ARGUS-01) — so the map shows more than one dot, and the
risk engine's spatial_agreement signal has other nodes to compare against.

After SPIKE_AFTER_S, ARGUS-02 and ARGUS-03 both start drifting toward a
shared anomaly (temperature climbing, humidity dropping) while ARGUS-04
stays at its normal baseline — this mirrors the spec's spatial-correlation
example almost exactly (2/3 nearby nodes abnormal = 67% spatial agreement).
"""
import math
import random
import time

import requests

BACKEND_URL = "http://localhost:8000"
SEND_INTERVAL_S = 2
SPIKE_AFTER_S = 30    # start drifting sooner — a demo shouldn't need a full minute of waiting first
RAMP_DURATION_S = 30  # complete the drift over 30s, not 60 — the rolling baseline (last 10 readings)
                       # partially "catches up" to a slow ramp, muting how anomalous it looks

# Small lat/lon offsets from ARGUS-01's location, just enough to place four
# distinct markers on the map.
NODES = {
    "ARGUS-02": {"lat": -27.4705, "lon": 153.0260, "base_temp": 23.5},
    "ARGUS-03": {"lat": -27.4690, "lon": 153.0245, "base_temp": 24.0},
    "ARGUS-04": {"lat": -27.4712, "lon": 153.0230, "base_temp": 24.2},
}
SPIKING_NODES = {"ARGUS-02", "ARGUS-03"}  # drift together; ARGUS-04 stays normal

start_time = time.time()


def build_reading(node_id, config):
    elapsed = time.time() - start_time
    temperature = config["base_temp"] + math.sin(elapsed / 25) * 0.3 + random.uniform(-0.2, 0.2)
    humidity = 55.0 + random.uniform(-1.2, 1.2)
    distance = 150.0 + random.uniform(-3, 3)

    if node_id in SPIKING_NODES and elapsed > SPIKE_AFTER_S:
        ramp = min((elapsed - SPIKE_AFTER_S) / RAMP_DURATION_S, 1.0)
        temperature += ramp * 12.0
        humidity -= ramp * 25.0

    return {
        "node_id": node_id,
        "temperature": round(temperature, 1),
        "humidity": round(max(humidity, 0), 1),
        "distance": round(max(distance, 5), 1),
        "sound": 40 + random.randint(-5, 5),
        "beam_status": "normal",
        "latitude": config["lat"],
        "longitude": config["lon"],
        "esp32_online": "true",
        "dht11_status": "OK",
        "hcsr04_status": "OK",
        "ir_beam_status": "OK",
        "network_status": "CONNECTED",
    }


def main():
    print(f"Simulating: {', '.join(NODES)}")
    print(f"ARGUS-02 and ARGUS-03 start drifting together after {SPIKE_AFTER_S}s "
          f"(ARGUS-04 stays at baseline) to demonstrate spatial agreement.")
    while True:
        for node_id, config in NODES.items():
            reading = build_reading(node_id, config)
            try:
                response = requests.post(f"{BACKEND_URL}/api/sensor-data", data=reading, timeout=5)
                print(f"{node_id}: temp={reading['temperature']}C humidity={reading['humidity']}% -> {response.status_code}")
            except requests.RequestException as error:
                print(f"{node_id}: POST failed: {error}")
        time.sleep(SEND_INTERVAL_S)


if __name__ == "__main__":
    main()
