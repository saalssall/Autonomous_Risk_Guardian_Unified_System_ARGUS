const FLAGS = ["person", "smoke", "water", "debris"];

export function CameraObservationPanel({ observation, backendUrl }) {
  return (
    <div className="panel camera-obs-panel">
      <p className="eyebrow">Latest visual observation</p>
      {!observation ? (
        <p className="empty-state">No camera upload for this node yet.</p>
      ) : (
        <>
          <div className="camera-frame">
            <img src={`${backendUrl.replace(/\/$/, "")}/${observation.image_url}`} alt="Latest camera observation" />
          </div>
          <p className="camera-captured">Captured {new Date(observation.timestamp).toLocaleTimeString()}</p>
          <ul className="observation-flags">
            {FLAGS.map((flag) => (
              <li key={flag} className={observation[flag] ? "flag-true" : "flag-false"}>
                <span>{flag}</span>
                <span>{observation[flag] ? `${Math.round(observation.confidence * 100)}%` : "not detected"}</span>
              </li>
            ))}
          </ul>
          {/* The schema stores one confidence value per observation, not one
              per flag — smoke/water/person/debris all share it when true.
              A per-flag confidence would need a schema change. */}
        </>
      )}
    </div>
  );
}
