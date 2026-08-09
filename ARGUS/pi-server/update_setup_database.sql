-- Updated Schema for Argus Telemetry Database
PRAGMA foreign_keys = ON;

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
);

-- Indexing for fast dashboard retrieval queries by node and time
CREATE INDEX IF NOT EXISTS idx_node_timestamp ON sensor_telemetry (node_id, timestamp);
