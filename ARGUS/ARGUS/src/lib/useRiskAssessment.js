import { useEffect, useRef, useState } from "react";
import { assessRisk } from "../lib/riskEngine"; 

const HISTORY_WINDOW_SIZE = 30; // keep last N readings per node for baseline calc

/**
 * Wires the risk engine into live data. Drop this in alongside useWebSocket:
 *
 *   const { sensorReadings, detections } = useWebSocket();
 *   const risk = useRiskAssessment(sensorReadings);
 *
 * `risk` is null until enough history has built up, then updates on every
 * new sensor reading. Keeps a separate rolling history per node_id, so this
 * works fine once you have more than one ARGUS node reporting.
 *
 * NOTE: corroboratingNodes/weatherAlignment/visionConfirmation are wired to
 * sensible defaults for now (see below) — hook these up to real multi-node
 * and weather/vision data as those pieces come online.
 */
export function useRiskAssessment(latestReading, options = {}) {
  const historyByNode = useRef(new Map());
  const [risk, setRisk] = useState(null);

  useEffect(() => {
    if (!latestReading?.node_id) return;

    const nodeId = latestReading.node_id;
    const timestampMs = latestReading.timestamp ? Date.parse(latestReading.timestamp) : Date.now();
    const reading = { ...latestReading, timestampMs };

    const history = historyByNode.current.get(nodeId) ?? [];

    // Compute risk BEFORE pushing current reading into history, so
    // "current vs baseline" doesn't include itself.
    const assessment = assessRisk(history, reading, {
      corroboratingNodes: options.corroboratingNodes ?? 0,
      weatherAlignment: options.weatherAlignment ?? null,
      visionConfirmation: options.visionConfirmation ?? null,
    });
    setRisk({ ...assessment, node_id: nodeId, timestamp: latestReading.timestamp });

    const updatedHistory = [...history, reading].slice(-HISTORY_WINDOW_SIZE);
    historyByNode.current.set(nodeId, updatedHistory);
  }, [latestReading, options.corroboratingNodes, options.weatherAlignment, options.visionConfirmation]);

  return risk;
}
