function formatTime(timestamp) {
  const date = timestamp ? new Date(timestamp) : new Date();
  return date.toLocaleTimeString([], { hour12: false });
}

export function DetectionLog({ detections }) {
  return (
    <div className="panel log-panel">
      <h2>Detections ({detections.length})</h2>
      {detections.length === 0 ? (
        <p className="empty-state">No detections yet — the log fills in as the rover spots something.</p>
      ) : (
        <ul className="log-list">
          {detections.map((detection) => (
            <li key={detection.id} className="log-item">
              <span className="log-label">{detection.label ?? "unknown"}</span>
              <span className="log-confidence">
                {detection.confidence != null ? `${Math.round(detection.confidence * 100)}%` : "—"}
              </span>
              <span className="log-time">{formatTime(detection.timestamp)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
