import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 3000;

export function useAuthorityData(backendUrl) {
  const [status, setStatus] = useState("idle"); // idle | connecting | open | error
  const [nodes, setNodes] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [nodeRiskHistory, setNodeRiskHistory] = useState([]);
  const [nodeHistory, setNodeHistory] = useState([]);
  const [nodeObservations, setNodeObservations] = useState([]);
  const [deviceHealth, setDeviceHealth] = useState(null);
  const timerRef = useRef(null);
  const selectedNodeIdRef = useRef(null);
  selectedNodeIdRef.current = selectedNodeId;

  const pollOnce = useCallback(async () => {
    const base = backendUrl.replace(/\/$/, "");
    try {
      const [nodesRes, alertsRes] = await Promise.all([
        fetch(`${base}/api/nodes`),
        fetch(`${base}/api/alerts`),
      ]);
      if (!nodesRes.ok || !alertsRes.ok) throw new Error("request failed");

      setNodes(await nodesRes.json());
      setAlerts(await alertsRes.json());

      const currentSelection = selectedNodeIdRef.current;
      if (currentSelection) {
        const [riskRes, historyRes, obsRes, healthRes] = await Promise.all([
          fetch(`${base}/api/risk/${currentSelection}?limit=20`),
          fetch(`${base}/api/history/${currentSelection}?limit=20`),
          fetch(`${base}/api/observations/${currentSelection}?limit=5`),
          fetch(`${base}/api/device-health/${currentSelection}`),
        ]);
        if (riskRes.ok) {
          const risk = await riskRes.json();
          setNodeRiskHistory([...risk].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)));
        }
        if (historyRes.ok) setNodeHistory(await historyRes.json());
        if (obsRes.ok) setNodeObservations(await obsRes.json());
        setDeviceHealth(healthRes.ok ? await healthRes.json() : null);
      }

      setStatus("open");
    } catch {
      setStatus("error");
    }
  }, [backendUrl]);

  useEffect(() => {
    setStatus("connecting");
    pollOnce();
    timerRef.current = setInterval(pollOnce, POLL_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [pollOnce]);

  const selectedNode = nodes.find((n) => n.node_id === selectedNodeId) ?? null;
  const latestRisk = nodeRiskHistory[nodeRiskHistory.length - 1] ?? null; // ascending sort — last is newest
  const latestReading = nodeHistory[0] ?? null; // history is newest-first from the API
  const previousReading = nodeHistory[1] ?? null;
  const latestObservation = nodeObservations[0] ?? null;

  return {
    status,
    nodes,
    alerts,
    selectedNodeId,
    setSelectedNodeId,
    selectedNode,
    nodeRiskHistory,
    latestRisk,
    latestReading,
    previousReading,
    latestObservation,
    deviceHealth,
  };
}
