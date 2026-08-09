import { useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 5000; // residents don't need 3s precision — less chatty than the authority view

export function useResidentData(backendUrl, nodeId) {
  const [status, setStatus] = useState("idle");
  const [latestRisk, setLatestRisk] = useState(null);
  const [node, setNode] = useState(null);
  const [latestObservation, setLatestObservation] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    const base = backendUrl.replace(/\/$/, "");

    async function poll() {
      try {
        const [riskRes, nodeRes, obsRes] = await Promise.all([
          fetch(`${base}/api/risk/${nodeId}?limit=1`),
          fetch(`${base}/api/nodes/${nodeId}`),
          fetch(`${base}/api/observations/${nodeId}?limit=1`),
        ]);
        if (riskRes.ok) {
          const risk = await riskRes.json();
          setLatestRisk(risk[0] ?? null);
        }
        if (nodeRes.ok) setNode(await nodeRes.json());
        if (obsRes.ok) {
          const obs = await obsRes.json();
          setLatestObservation(obs[0] ?? null);
        }
        setStatus("open");
      } catch {
        setStatus("error");
      }
    }

    setStatus("connecting");
    poll();
    timerRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [backendUrl, nodeId]);

  return { status, latestRisk, node, latestObservation };
}
