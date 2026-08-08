"""
Mock ARGUS sensor node — for testing the dashboard without real hardware.
 
Sends the exact same JSON shape as the real ESP32 firmware, over the same
WebSocket protocol as detect_server.py, so the dashboard can't tell the
difference. Values drift slowly and realistically, then ramp distance_cm
down and humidity up around the 60s mark to simulate a rising water level —
this should walk the risk engine from LOW up through the tiers, so you can
watch RiskPanel/EvidencePanel actually respond to real signal instead of
just showing "establishing baseline" forever.
 
Run this INSTEAD of the ESP32 (not alongside it) while testing the dashboard.
It connects to the same Pi WebSocket server as the real firmware would, so
detect_server.py should already be running.
 
Install: pip install websockets
Run:     python3 mock_sensor.py
"""
 
import asyncio
import json
import math
import random
import time
 
import websockets
 
PI_URL = "ws://localhost:8765"  # change to the Pi's address if testing remotely
NODE_ID = "ARGUS-01"
SEND_INTERVAL_S = 2
 
start_time = time.time()
 
 
def build_reading():
    elapsed = time.time() - start_time
 
    # Baseline values with small natural jitter.
    temperature = 24.0 + math.sin(elapsed / 20) * 0.8 + random.uniform(-0.3, 0.3)
    humidity = 55.0 + random.uniform(-2, 2)
    distance_cm = 150.0 + random.uniform(-3, 3)
    sound_level = 40 + random.randint(-5, 5)
 
    # After 60s, simulate rising water: distance drops, humidity climbs.
    # This should be enough to push the risk engine past LOW/GUARDED.
    if elapsed > 60:
        ramp = min((elapsed - 60) / 60, 1.0)  # ramps over 60s, then holds
        distance_cm -= ramp * 90  # water rising toward the sensor
        humidity += ramp * 25
 
    return {
        "type": "sensor",
        "node_id": NODE_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latitude": -27.5000,
        "longitude": 153.0500,
        "temperature": round(temperature, 1),
        "humidity": round(max(humidity, 0), 1),
        "distance_cm": round(max(distance_cm, 5), 1),
        "sound_level": sound_level,
        "beam_status": "normal",
        "battery": 91,
        "device_health": 98,
    }
 
 
async def main():
    async with websockets.connect(PI_URL) as ws:
        print(f"Connected to {PI_URL} as {NODE_ID} — sending a reading every {SEND_INTERVAL_S}s")
        print("Simulated flood ramp begins at ~60s from now")
        while True:
            reading = build_reading()
            await ws.send(json.dumps(reading))
            print(f"sent: temp={reading['temperature']}  distance={reading['distance_cm']}cm  humidity={reading['humidity']}%")
            await asyncio.sleep(SEND_INTERVAL_S)
 
 
if __name__ == "__main__":
    asyncio.run(main())
 