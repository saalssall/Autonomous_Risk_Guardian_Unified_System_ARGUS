import sqlite3
import json

DB_FILE = "argus.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def insert_sensor_telemetry(data: dict):
    """Inserts raw telemetry payload into local SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Convert device_health dict to a JSON string for SQLite storage
    device_health_str = json.dumps(data.get("device_health", {}))
    
    cursor.execute("""
        INSERT INTO sensor_telemetry (node_id, temperature, humidity, distance, device_health, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("node_id"),
        data.get("temperature"),
        data.get("humidity"),
        data.get("distance"),
        device_health_str,
        data.get("status", "normal")
    ))
    
    conn.commit()
    conn.close()

def get_latest_telemetry(node_id: str):
    """Retrieves the most recent record for a specific node from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_telemetry 
        WHERE node_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (node_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data = dict(row)
        if data.get("device_health"):
            data["device_health"] = json.loads(data["device_health"])
        return data
    return None

def get_node_history(node_id: str, limit: int = 50):
    """Retrieves historical sensor telemetry for trend analysis."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_telemetry 
        WHERE node_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (node_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        data = dict(row)
        if data.get("device_health"):
            data["device_health"] = json.loads(data["device_health"])
        history.append(data)
        
    return history[::-1] # Return in chronological order

def get_all_active_nodes():
    """Retrieves the latest state for active nodes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_telemetry 
        ORDER BY timestamp DESC 
        LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    
    nodes = []
    for row in rows:
        data = dict(row)
        if data.get("device_health"):
            data["device_health"] = json.loads(data["device_health"])
        nodes.append(data)
        
    return nodes
