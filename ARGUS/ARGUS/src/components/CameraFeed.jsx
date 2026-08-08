import { useState } from "react";

function authenticatedStreamUrl(streamUrl) {
  const token = sessionStorage.getItem("argusAccessToken");

  if (!streamUrl || !token) return null;

  const url = new URL(streamUrl);
  url.searchParams.set("token", token);
  return url.toString();
}

export function CameraFeed({ streamUrl, detection }) {
  const [errored, setErrored] = useState(false);
  const securedUrl = authenticatedStreamUrl(streamUrl);

  return (
    <section className="camera-panel panel">
      <p className="eyebrow">Latest visual feed</p>

      <div className="camera-frame">
        {securedUrl && !errored ? (
          <img
            src={securedUrl}
            alt="Live ARGUS camera feed"
            onError={() => setErrored(true)}
          />
        ) : (
          <div className="feed-placeholder">
            <span>◉</span>
            <p>Awaiting authenticated node camera feed</p>
          </div>
        )}
      </div>

      <div className="feed-meta">
        <span>Captured: {securedUrl ? "live" : "—"}</span>
        <strong>
          {detection
            ? `${detection.label ?? "Environmental observation"} · ${Math.round(
                (detection.confidence ?? 0) * 100
              )}%`
            : "Visual classification pending"}
        </strong>
      </div>
    </section>
  );
}