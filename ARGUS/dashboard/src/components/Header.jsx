const STATUS_LABEL = {
  idle: "Not connected",
  connecting: "Connecting…",
  open: "Live",
  error: "Backend unreachable",
};

export function Header({ status }) {
  return (
    <header className="header">
      <div>
        <h1>Rubble Rover</h1>
        <p className="subtitle">Ops dashboard</p>
      </div>
      <div className={`status-badge status-${status}`}>
        <span className="status-dot" />
        {STATUS_LABEL[status]}
      </div>
    </header>
  );
}
