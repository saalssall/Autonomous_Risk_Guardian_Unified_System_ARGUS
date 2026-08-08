import "./risk-panels.css";

// risk: the object returned by useRiskAssessment() — see riskEngine.js
export function EvidencePanel({ risk }) {
  if (!risk) return null;

  const { explanation, evidence, device_health } = risk;

  return (
    <div className="panel evidence-panel">
      <h2>AI explanation &amp; evidence</h2>
      <p className="evidence-panel__explanation">{explanation}</p>

      {evidence?.length > 0 && (
        <ul className="evidence-checklist">
          {evidence.map((item) => (
            <li
              key={item.label}
              className={item.met ? "evidence-checklist__item evidence-checklist__item--met" : "evidence-checklist__item evidence-checklist__item--unmet"}
            >
              <span className="evidence-checklist__mark" aria-hidden="true">
                {item.met ? "✓" : "○"}
              </span>
              {item.label}
            </li>
          ))}
        </ul>
      )}

      {device_health && device_health.status !== "HEALTHY" && (
        <p className="evidence-panel__caveat">
          Node hardware is {device_health.status.toLowerCase()} ({device_health.faultReasons.join(", ")}) —
          confidence reduced accordingly. See Device Integrity panel for detail.
        </p>
      )}
    </div>
  );
}
