import { useState } from "react";

// This backend only stores periodic snapshot uploads (POST /api/image), not
// a live stream — so this shows the latest snapshot, refreshed each poll,
// rather than continuous video like the earlier WebSocket-based version did.
export function CameraFeed({ imageUrl, detection }) {
  const [errored, setErrored] = useState(false);

  return (
    <section className="camera-panel panel">
      <p className="eyebrow">Latest snapshot</p>

      <div className="camera-frame">
        {imageUrl && !errored ? (
          <img
            key={imageUrl}
            src={imageUrl}
            alt="Latest ARGUS camera snapshot"
            onError={() => setErrored(true)}
          />
        ) : (
          <div className="feed-placeholder">
            <span>◉</span>
            <p>Waiting for the first camera upload from this node.</p>
          </div>
        )}
      </div>

      <div className="feed-meta">
        <span>Captured: {imageUrl ? "latest snapshot" : "—"}</span>
        <strong>
          {detection
            ? `${detection.label} · ${Math.round((detection.confidence ?? 0) * 100)}%`
            : "No flagged detections yet"}
        </strong>
      </div>
    </section>
  );
}
