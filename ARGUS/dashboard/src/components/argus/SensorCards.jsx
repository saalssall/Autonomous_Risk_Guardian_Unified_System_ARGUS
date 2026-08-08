const FIELDS = [
  { key: "temperature", label: "Temperature", unit: "°C" },
  { key: "humidity", label: "Humidity", unit: "%" },
  { key: "distance", label: "Distance", unit: "cm" },
];

function ChangeIndicator({ current, previous, unit }) {
  if (current == null || previous == null) return <span className="sensor-change">— no prior reading</span>;
  const delta = current - previous;
  const arrow = delta > 0 ? "↑" : delta < 0 ? "↓" : "→";
  const sign = delta > 0 ? "+" : "";
  return (
    <span className="sensor-change">
      {arrow} {sign}{delta.toFixed(1)}{unit}
    </span>
  );
}

export function SensorCards({ latestReading, previousReading }) {
  return (
    <div className="panel sensor-cards-panel">
      <p className="eyebrow">Sensor readings</p>
      {!latestReading ? (
        <p className="empty-state">Select a node to see its sensor readings.</p>
      ) : (
        <div className="sensor-cards">
          {FIELDS.map(({ key, label, unit }) => (
            <div className="sensor-card" key={key}>
              <span className="sensor-card-label">{label}</span>
              <span className="sensor-card-value">{latestReading[key]}{unit}</span>
              <ChangeIndicator current={latestReading[key]} previous={previousReading?.[key]} unit={unit} />
              <span className="sensor-card-period">vs. previous reading</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
