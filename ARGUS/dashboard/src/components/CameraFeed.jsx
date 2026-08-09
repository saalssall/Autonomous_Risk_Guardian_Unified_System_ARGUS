import { useState } from "react";

// Now backed by the Pi's live MJPEG stream (see detect_server.py's /stream
// endpoint) instead of polling stored snapshots — the <img> tag renders an
// MJPEG multipart stream natively, so this updates continuously with no
// polling logic needed.
export function CameraFeed({ streamUrl, detection }) {
  const [errored, setErrored] = useState(false);

  return (
    <section className="camera-panel panel">
      <p className="eyebrow">Live feed</p>

      <div className="camera-frame">
        {streamUrl && !errored ? (
          <img
            key={streamUrl}
            src={streamUrl}
            alt="ARGUS live camera feed"
            onError={() => setErrored(true)}
          />
        ) : (
          <div className="feed-placeholder">
            <span>◉</span>
            <p>
              {errored
                ? "Camera feed unreachable — check the node's connection."
                : "Waiting for the camera stream from this node."}
            </p>
          </div>
        )}
      </div>

      <div className="feed-meta">
        <span>{streamUrl && !errored ? "Streaming" : "—"}</span>
        <strong>
          {detection
            ? `${detection.label} · ${Math.round((detection.confidence ?? 0) * 100)}%`
            : "No flagged detections yet"}
        </strong>
      </div>
    </section>
  );
}