CREATE TABLE sensor_telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    node_id TEXT NOT NULL,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    distance REAL NOT NULL,
    device_health TEXT NOT NULL,
    status TEXT DEFAULT 'normal'
);