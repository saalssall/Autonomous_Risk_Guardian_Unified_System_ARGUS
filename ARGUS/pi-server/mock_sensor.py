"""Mock authenticated ARGUS sensor node for dashboard testing."""
import asyncio
import json
import math
import os
import random
import time

import websockets

PI_URL = os.getenv("ARGUS_PI_URL", "ws://localhost:8765")
SENSOR_TOKEN = os.getenv("ARGUS_SENSOR_TOKEN", "")
NODE_ID = os.getenv("ARGUS_NODE_ID", "ARGUS-01")
SEND_INTERVAL_S = 2
start_time = time.time()

if len(SENSOR_TOKEN) < 24:
    raise RuntimeError("Set ARGUS_SENSOR_TOKEN to the sensor token from the Pi server .env.")


def build_reading():
    elapsed = time.time() - start_time
    temperature = 24.0 + math.sin(elapsed / 20) * 0.8 + random.uniform(-0.3, 0.3)
    humidity = 55.0 + random.uniform(-2, 2)
    distance_cm = 150.0 + random.uniform(-3, 3)
    if elapsed > 60:
        ramp = min((elapsed - 60) / 60, 1.0)
        distance_cm -= ramp * 90
        humidity += ramp * 25
    return {"type": "sensor", "node_id": NODE_ID, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "latitude": -27.5, "longitude": 153.05, "temperature": round(temperature, 1), "humidity": round(max(humidity, 0), 1), "distance_cm": round(max(distance_cm, 5), 1), "sound_level": 40 + random.randint(-5, 5), "beam_status": "normal", "battery": 91, "device_health": 98}


async def main():
    async with websockets.connect(PI_URL, max_size=8192, compression=None) as ws:
        await ws.send(json.dumps({"type": "auth", "role": "sensor", "token": SENSOR_TOKEN}))
        reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if reply.get("type") != "auth_ok" or reply.get("role") != "sensor":
            raise RuntimeError("Pi server rejected the sensor credentials.")
        print(f"Connected to {PI_URL} as {NODE_ID}; flood simulation starts after 60 seconds.")
        while True:
            reading = build_reading()
            await ws.send(json.dumps(reading, separators=(",", ":")))
            print(f"sent: distance={reading['distance_cm']}cm humidity={reading['humidity']}%")
            await asyncio.sleep(SEND_INTERVAL_S)


if __name__ == "__main__":
    asyncio.run(main())
