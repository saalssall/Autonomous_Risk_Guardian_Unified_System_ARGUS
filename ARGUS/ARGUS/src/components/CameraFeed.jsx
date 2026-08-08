import { useState } from "react";

export function CameraFeed({ streamUrl }) {
  const [errored, setErrored] = useState(false);

  return (
    <div className="panel camera-panel">
      <h2>Camera feed</h2>
      <div className="camera-frame">
        {!streamUrl ? (
          <p className="empty-state">Waiting for a feed URL — set the rover address to begin.</p>
        ) : errored ? (
          <p className="empty-state">Feed unavailable. Check the rover is streaming.</p>
        ) : (
          <img
            src={streamUrl}
            alt="Live rover camera feed"
            onError={() => setErrored(true)}
            onLoad={() => setErrored(false)}
          />
        )}
      </div>
    </div>
  );
}
