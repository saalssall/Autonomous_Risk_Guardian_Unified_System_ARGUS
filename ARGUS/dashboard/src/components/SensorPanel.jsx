// Expects sensorReadings shaped like what useBackendData.js assembles from
// GET /api/history/{node_id} + GET /api/nodes/{node_id}:
// { node_id, temperature, humidity, distance_cm, sound_level, beam_status, battery, status }
const FIELDS = [
  { key: "temperature", label: "Temperature", unit: "°C" },
  { key: "humidity", label: "Humidity", unit: "%" },
  { key: "distance_cm", label: "Distance", unit: "cm" },
  { key: "sound_level", label: "Sound level", unit: "" },
  { key: "battery", label: "Battery", unit: "%" },
  { key: "status", label: "Node status", unit: "" },
];

export function SensorPanel({ readings }) {
  return (
    <div className="panel sensor-panel">
      <h2>Sensor readings{readings?.node_id ? ` — ${readings.node_id}` : ""}</h2>
      {!readings ? (
        <p className="empty-state">Waiting for the first reading from the ESP32.</p>
      ) : (
        <>
          <dl className="sensor-grid">
            {FIELDS.map(({ key, label, unit }) => (
              <div className="sensor-field" key={key}>
                <dt>{label}</dt>
                <dd>{readings[key] != null ? `${readings[key]}${unit}` : "—"}</dd>
              </div>
            ))}
          </dl>
          {readings.beam_status === "broken" && <p className="beam-alert">Beam-break triggered</p>}
        </>
      )}
    </div>
  );
}
