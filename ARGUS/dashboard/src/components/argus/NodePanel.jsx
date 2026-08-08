const TREND_ARROW = { increasing: "↑", decreasing: "↓", steady: "→" };

function timeAgo(isoString) {
  if (!isoString) return "—";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

export function NodePanel({ node, latestRisk }) {
  if (!node) {
    return (
      <div className="panel node-panel">
        <p className="eyebrow">Selected node</p>
        <p className="empty-state">Click a node on the map to see its detail.</p>
      </div>
    );
  }

  return (
    <div className="panel node-panel">
      <p className="eyebrow">{node.node_id}</p>

      {latestRisk ? (
        <div className="risk-block">
          <div className="risk-level">{latestRisk.risk_level}</div>
          <div className="risk-percent">
            {latestRisk.risk_score}% <span className="risk-trend">{TREND_ARROW[latestRisk.trend]} {latestRisk.trend}</span>
          </div>
          {latestRisk.hazard && <p className="risk-note">Hazard signal: {latestRisk.hazard.replace(/_/g, " ")}</p>}
          <div className="risk-confidence">Confidence {Math.round(latestRisk.confidence)}%</div>
        </div>
      ) : (
        <p className="empty-state">No risk assessments recorded yet for this node.</p>
      )}

      <dl className="node-meta">
        <div>
          <dt>Device</dt>
          <dd className={node.status === "HEALTHY" ? "meta-ok" : "meta-warn"}>{node.status}</dd>
        </div>
        <div>
          <dt>Battery</dt>
          <dd>{node.battery}%</dd>
        </div>
        <div>
          <dt>Last update</dt>
          <dd>{timeAgo(node.last_seen)}</dd>
        </div>
      </dl>
    </div>
  );
}
