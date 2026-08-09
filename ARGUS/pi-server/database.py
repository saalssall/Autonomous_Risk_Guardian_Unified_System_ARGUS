import sqlite3
import json

DB_NAME = "argus_telementry.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            node_id TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            distance REAL NOT NULL,
            device_health TEXT NOT NULL,
            health_percentage REAL NOT NULL,
            spatial_agreement REAL DEFAULT 100.0,
            status TEXT DEFAULT 'normal'
        )
    """)
    conn.commit()
    conn.close()

def insert_telemetry(node_id, temperature, humidity, distance, device_health, health_percentage, spatial_agreement, status='normal'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_telemetry (node_id, temperature, humidity, distance, device_health, health_percentage, spatial_agreement, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (node_id, temperature, humidity, distance, json.dumps(device_health), health_percentage, spatial_agreement, status))
    conn.commit()
    conn.close()

def fetch_latest_telemetry(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_telemetry ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
