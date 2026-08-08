import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 3000;
const MAX_DETECTIONS = 50;

// One camera_observations row can carry up to 4 true flags (person, smoke,
// water, debris) — split it into one synthetic "detection" per true flag so
// DetectionLog can show them individually, same shape as before.
function detectionsFromObservation(observation) {
  const flags = ["person", "smoke", "water", "debris"];
  return flags
    .filter((flag) => observation[flag])
    .map((flag) => ({
      id: `${observation.id}-${flag}`,
      label: flag,
      confidence: observation.confidence,
      timestamp: observation.timestamp,
    }));
}

// Polls the FastAPI backend instead of holding a live connection — this
// backend has no WebSocket/push mechanism, only REST endpoints. Status is
// "open" as long as the last poll succeeded.
export function useBackendData() {
  const [status, setStatus] = useState("idle"); // idle | connecting | open | error
  const [sensorReadings, setSensorReadings] = useState(null);
  const [detections, setDetections] = useState([]);
  const [latestImageUrl, setLatestImageUrl] = useState(null);
  const configRef = useRef(null); // { backendUrl, nodeId }
  const timerRef = useRef(null);
  const seenObservationIds = useRef(new Set());

  const pollOnce = useCallback(async () => {
    const config = configRef.current;
    if (!config) return;
    const { backendUrl, nodeId } = config;

    try {
      const [historyRes, nodeRes, observationsRes] = await Promise.all([
        fetch(`${backendUrl}/api/history/${nodeId}?limit=1`),
        fetch(`${backendUrl}/api/nodes/${nodeId}`),
        fetch(`${backendUrl}/api/observations/${nodeId}?limit=10`),
      ]);
      if (!historyRes.ok || !nodeRes.ok || !observationsRes.ok) {
        throw new Error("request failed");
      }

      const [latestReading] = await historyRes.json();
      const node = await nodeRes.json();
      const observations = await observationsRes.json();

      if (latestReading) {
        setSensorReadings({
          node_id: nodeId,
          temperature: latestReading.temperature,
          humidity: latestReading.humidity,
          distance_cm: latestReading.distance,
          sound_level: latestReading.sound,
          beam_status: latestReading.beam_status,
          battery: node?.battery,
          status: node?.status,
        });
      }

      if (observations.length > 0) {
        // Only append genuinely new observations, not ones already in the log
        // from a previous poll — otherwise every poll would re-add the same rows.
        const fresh = observations.filter((obs) => !seenObservationIds.current.has(obs.id));
        fresh.forEach((obs) => seenObservationIds.current.add(obs.id));
        if (fresh.length > 0) {
          const newDetections = fresh.flatMap(detectionsFromObservation);
          if (newDetections.length > 0) {
            setDetections((prev) => [...newDetections, ...prev].slice(0, MAX_DETECTIONS));
          }
        }
        setLatestImageUrl(`${backendUrl}/${observations[0].image_url}`);
      }

      setStatus("open");
    } catch {
      setStatus("error");
    }
  }, []);

  const connect = useCallback(
    (backendUrl, nodeId) => {
      configRef.current = { backendUrl: backendUrl.replace(/\/$/, ""), nodeId };
      seenObservationIds.current.clear();
      setStatus("connecting");
      if (timerRef.current) clearInterval(timerRef.current);
      pollOnce(); // fire immediately instead of waiting for the first interval tick
      timerRef.current = setInterval(pollOnce, POLL_INTERVAL_MS);
    },
    [pollOnce]
  );

  const disconnect = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    configRef.current = null;
    setStatus("idle");
  }, []);

  useEffect(() => disconnect, [disconnect]); // stop polling on unmount

  return { status, sensorReadings, detections, latestImageUrl, connect, disconnect };
}
