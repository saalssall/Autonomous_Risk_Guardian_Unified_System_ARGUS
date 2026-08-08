// Real device-condition data from the ESP32's most recent reading, via
// GET /api/device-health/{node_id} — no longer client-side approximated.
const FIELDS = [
  { key: "esp32_online", label: "ESP32", trueLabel: "ONLINE", falseLabel: "OFFLINE" },
  { key: "dht11_status", label: "Temp/humidity sensor" },
  { key: "hcsr04_status", label: "Ultrasonic sensor" },
  { key: "ir_beam_status", label: "Beam sensor" },
  { key: "network_status", label: "Network", trueValue: "CONNECTED" },
];

function isOk(value, field) {
  if (value == null) return null;
  if (field.key === "esp32_online") return value === true;
  if (field.key === "network_status") return value === "CONNECTED";
  return value === "OK";
}

function displayValue(value, field) {
  if (value == null) return "UNKNOWN";
  if (field.key === "esp32_online") return value ? field.trueLabel : field.falseLabel;
  return value;
}

export function DeviceHealthPanel({ deviceHealth, hasSelection }) {
  return (
    <div className="panel device-health-panel">
      <p className="eyebrow">Device health</p>
      {!hasSelection ? (
        <p className="empty-state">Select a node to see its device health.</p>
      ) : !deviceHealth ? (
        <p className="empty-state">No readings for this node yet.</p>
      ) : (
        <ul className="device-health-list">
          {FIELDS.map((field) => {
            const raw = deviceHealth[field.key];
            const ok = isOk(raw, field);
            return (
              <li key={field.key}>
                <span>{field.label}</span>
                <span className={ok === null ? "meta-unknown" : ok ? "meta-ok" : "meta-warn"}>
                  {displayValue(raw, field)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
