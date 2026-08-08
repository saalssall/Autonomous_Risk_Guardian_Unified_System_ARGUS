import "./risk-panels.css";

const RISK_COLOR_VAR = {
  LOW: "var(--risk-low)",
  GUARDED: "var(--risk-guarded)",
  ELEVATED: "var(--risk-elevated)",
  HIGH: "var(--risk-high)",
  CRITICAL: "var(--risk-critical)",
};

const METRIC_META = {
  temperature: { label: "Temperature", unit: "°C" },
  humidity: { label: "Humidity", unit: "%" },
  distance_cm: { label: "Water level (proxy)", unit: "cm" },
  sound_level: { label: "Sound", unit: "" },
};

const DIRECTION_ARROW = { increasing: "↑", decreasing: "↓", stable: "→" };

// risk: the object returned by useRiskAssessment() — see riskEngine.js
export function RiskPanel({ risk }) {
  if (!risk) {
    return (
      <div className="panel risk-panel risk-panel--pending">
        <h2>Current situation</h2>
        <p className="empty-state">Establishing baseline — need a few more readings before a risk call can be made.</p>
      </div>
    );
  }

  const { risk_level, confidence, hazard_category, timestamp, trends, projection } = risk;

  return (
    <div className="panel risk-panel" style={{ "--risk-color": RISK_COLOR_VAR[risk_level] }}>
      <div className="risk-panel__header">
        <h2>Current situation</h2>
        {timestamp && (
          <span className="risk-panel__timestamp">
            {new Date(timestamp).toLocaleTimeString([], { hour12: false })}
          </span>
        )}
      </div>

      <div className="risk-badge">
        <span className="risk-badge__dot" aria-hidden="true" />
        <span className="risk-badge__level">{risk_level}</span>
        <span className="risk-badge__confidence">{Math.round(confidence * 100)}% confidence</span>
      </div>

      <p className="risk-panel__hazard">{hazard_category}</p>

      {trends.length > 0 && (
        <table className="trend-table">
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Trend</th>
              <th scope="col">Window</th>
              <th scope="col">Δ</th>
              <th scope="col">Δ%</th>
            </tr>
          </thead>
          <tbody>
            {trends.map((t) => {
              const meta = METRIC_META[t.key] ?? { label: t.key, unit: "" };
              return (
                <tr key={t.key}>
                  <th scope="row">{meta.label}</th>
                  <td className={`trend-direction trend-direction--${t.direction}`}>
                    <span aria-hidden="true">{DIRECTION_ARROW[t.direction]}</span> {t.direction}
                  </td>
                  <td>{t.timeFrameMinutes}m</td>
                  <td>
                    {t.absoluteDelta > 0 ? "+" : ""}
                    {t.absoluteDelta}
                    {meta.unit}
                  </td>
                  <td>{t.percentDelta != null ? `${t.percentDelta > 0 ? "+" : ""}${t.percentDelta}%` : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {projection && (
        <div className="projection-row">
          <span className="projection-row__label">Risk evolution</span>
          <div className="projection-row__steps">
            <div className="projection-step">
              <span>Now</span>
              <strong>{projection.now}%</strong>
            </div>
            <div className="projection-step">
              <span>+30m</span>
              <strong>{projection.plus30m}%</strong>
            </div>
            <div className="projection-step">
              <span>+60m</span>
              <strong>{projection.plus60m}%</strong>
            </div>
            <div className="projection-step">
              <span>+90m</span>
              <strong>{projection.plus90m}%</strong>
            </div>
          </div>
          <p className="projection-row__note">{projection.note}</p>
        </div>
      )}
    </div>
  );
}
