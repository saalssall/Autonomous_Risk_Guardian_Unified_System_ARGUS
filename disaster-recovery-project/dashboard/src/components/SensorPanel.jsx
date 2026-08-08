// Expects sensorReadings shaped like what the ESP32 will send:
// { type: "sensor", temperature, humidity, distance_cm, sound_level, beam_broken, timestamp }
// Adjust the field list below if the firmware ends up naming things differently.
const FIELDS = [
  { key: "temperature", label: "Temperature", unit: "°C" },
  { key: "humidity", label: "Humidity", unit: "%" },
  { key: "distance_cm", label: "Distance", unit: "cm" },
  { key: "sound_level", label: "Sound level", unit: "" },
  { key: "battery_v", label: "Battery", unit: "V" },
];

export function SensorPanel({ readings }) {
  return (
    <div className="panel sensor-panel">
      <h2>Sensor readings</h2>
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
          {readings.beam_broken && <p className="beam-alert">Beam-break triggered</p>}
        </>
      )}
    </div>
  );
}
