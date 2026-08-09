import { Link } from "react-router-dom";
import { ResidentMap } from "../components/resident/ResidentMap";
import { useResidentData } from "../hooks/useResidentData";

// There's no real geographic-to-node mapping yet (e.g. by address or GPS) —
// this just shows one fixed node as "your area". A real deployment would
// resolve this from the resident's actual location instead of a constant.
const RESIDENT_NODE_ID = "ARGUS-01";

const WHAT_IT_MEANS = {
  LOW: "Conditions in your area are within normal ranges.",
  GUARDED: "Conditions in your area are being monitored closely.",
  ELEVATED: "Conditions in your area are currently above normal levels and should be monitored.",
  HIGH: "Conditions in your area indicate a developing hazard.",
  CRITICAL: "Conditions in your area indicate a serious and immediate hazard.",
};

const RECOMMENDED_ACTION = {
  LOW: "No action needed. Continue as normal.",
  GUARDED: "Stay aware of local conditions.",
  ELEVATED: "Monitor official emergency updates. Prepare to move if instructed.",
  HIGH: "Follow official emergency instructions closely. Be ready to evacuate.",
  CRITICAL: "Evacuate immediately if instructed by authorities. Follow official emergency guidance.",
};

function timeAgo(isoString) {
  if (!isoString) return "—";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 1000));
  if (seconds < 60) return `${seconds} sec ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  return `${Math.floor(seconds / 3600)} hr ago`;
}

export function ResidentView({ backendUrl }) {
  const { status, latestRisk, node, latestObservation } = useResidentData(backendUrl, RESIDENT_NODE_ID);
  const riskLevel = latestRisk?.risk_level;

  return (
    <div className="resident-app">
      <div className="view-switch">
        <Link to="/">Switch to authority view →</Link>
      </div>

      <h1 className="resident-title">ARGUS</h1>
      <p className="resident-subtitle">Your area</p>

      {status !== "open" ? (
        <p className="empty-state resident-empty">
          {status === "error" ? "Unable to reach the monitoring system right now." : "Checking your area…"}
        </p>
      ) : !latestRisk ? (
        <p className="empty-state resident-empty">No conditions recorded for your area yet.</p>
      ) : (
        <>
          <div className={`resident-status resident-status-${riskLevel?.toLowerCase()}`}>{riskLevel}</div>

          <p className="resident-meaning">{WHAT_IT_MEANS[riskLevel] ?? "Status unavailable."}</p>

          <div className="resident-section">
            <span className="eyebrow">What changed</span>
            <p>
              Risk {latestRisk.trend ?? "steady"}
              <br />
              Last updated {timeAgo(latestRisk.timestamp)}
            </p>
          </div>

          <div className="resident-section resident-action">
            <span className="eyebrow">What to do</span>
            <p>{RECOMMENDED_ACTION[riskLevel] ?? "Follow official emergency guidance."}</p>
          </div>

          <div className="resident-section">
            <span className="eyebrow">Local map</span>
            <ResidentMap latitude={node?.latitude} longitude={node?.longitude} riskLevel={riskLevel} />
          </div>

          {latestObservation && (
            <div className="resident-section">
              <span className="eyebrow">Latest area image</span>
              <div className="resident-camera-frame">
                <img
                  src={`${backendUrl.replace(/\/$/, "")}/${latestObservation.image_url}`}
                  alt="Latest view of your area"
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
