export function ArgusHeader({ status, nodes, alerts }) {
  const healthy = nodes.filter((n) => n.status === "HEALTHY").length;
  const degraded = nodes.filter((n) => n.status === "DEGRADED").length;

  return (
    <header className="argus-header">
      <div>
        <h1>ARGUS</h1>
        <p className="subtitle">Autonomous Risk Guardian Unified System</p>
      </div>
      <div className="argus-stats">
        <div className={`status-badge status-${status}`}>
          <span className="status-dot" />
          {status === "open" ? "Operational" : status === "connecting" ? "Connecting…" : "Backend unreachable"}
        </div>
        <div className="stat">
          <span className="stat-value">{nodes.length}</span>
          <span className="stat-label">Active nodes</span>
        </div>
        <div className="stat">
          <span className="stat-value">{healthy}</span>
          <span className="stat-label">Healthy</span>
        </div>
        <div className="stat">
          <span className="stat-value">{degraded}</span>
          <span className="stat-label">Degraded</span>
        </div>
        <div className="stat">
          <span className="stat-value">{alerts.length}</span>
          <span className="stat-label">Active alerts</span>
        </div>
      </div>
    </header>
  );
}
