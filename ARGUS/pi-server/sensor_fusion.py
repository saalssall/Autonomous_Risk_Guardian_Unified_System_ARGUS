import datetime

def process_sensor_fusion(node_id: str, readings: list, camera_obs: list):
    """
    Fuses raw sensor readings and camera observations into a structured payload
    following the Core Rule: Never calculate risk off a single raw value.
    """
    if not readings:
        return None

    # Get latest absolute values
    latest_reading = readings[-1]
    temp = latest_reading.temperature
    humidity = latest_reading.humidity

    # Compute mock rate of change (e.g., 30-minute delta if history permits)
    temp_change_30m = 0.0
    if len(readings) > 1:
        temp_change_30m = temp - readings[-2].temperature

    # Check latest vision AI flags if available
    smoke_detected = False
    water_detected = False
    if camera_obs:
        latest_cam = camera_obs[-1]
        smoke_detected = latest_cam.smoke
        water_detected = latest_cam.water

    # Construct the Standard Internal Representation Payload
    fused_payload = {
        "region": "North Sector",
        "temperature": temp,
        "temperature_change_30m": temp_change_30m,
        "humidity": humidity,
        "camera_smoke": smoke_detected,
        "camera_water": water_detected,
        "risk_projection_timeline": {
            "now": "38%",
            "+30 min": "51%",
            "+60 min": "69%",
            "+90 min": "82%"
        }
    }
    
    return fused_payload
