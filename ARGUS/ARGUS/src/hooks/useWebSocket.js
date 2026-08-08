import { useCallback, useEffect, useRef, useState } from "react";

const MAX_DETECTIONS = 50;
const MAX_MESSAGE_BYTES = 8_192;

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isSafeTelemetry(data) {
  if (!isRecord(data) || typeof data.type !== "string") return false;

  if (data.type === "detection") {
    return (
      typeof data.label === "string" &&
      data.label.length <= 80 &&
      Number.isFinite(Number(data.confidence)) &&
      Number(data.confidence) >= 0 &&
      Number(data.confidence) <= 1
    );
  }

  return (
    data.type === "sensor" &&
    typeof data.node_id === "string" &&
    data.node_id.length > 0 &&
    data.node_id.length <= 64
  );
}

export function useWebSocket() {
  const [status, setStatus] = useState("idle");
  const [detections, setDetections] = useState([]);
  const [sensorReadings, setSensorReadings] = useState(null);
  const socketRef = useRef(null);

  const disconnect = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
  }, []);

  const connect = useCallback(
    (url, token) => {
      disconnect();
      setStatus("connecting");

      const accessToken = token || sessionStorage.getItem("argusAccessToken");

      let socket;
      try {
        socket = new WebSocket(url);
      } catch {
        setStatus("error");
        return;
      }

      socketRef.current = socket;

      socket.onopen = () => {
        setStatus("authenticating");
        socket.send(
          JSON.stringify({
            type: "auth",
            role: "dashboard",
            token: accessToken,
          })
        );
      };

      socket.onclose = () => setStatus("closed");
      socket.onerror = () => setStatus("error");

      socket.onmessage = (event) => {
        try {
          if (
            typeof event.data !== "string" ||
            event.data.length > MAX_MESSAGE_BYTES
          ) {
            return;
          }

          const data = JSON.parse(event.data);

          if (data.type === "auth_ok") {
            setStatus("open");
            return;
          }

          if (!isSafeTelemetry(data)) return;

          if (data.type === "sensor") {
            setSensorReadings(data);
          } else if (data.type === "detection") {
            setDetections((previous) =>
              [
                { ...data, id: crypto.randomUUID() },
                ...previous,
              ].slice(0, MAX_DETECTIONS)
            );
          }
        } catch {
          // Ignore malformed messages.
        }
      };
    },
    [disconnect]
  );

  useEffect(() => disconnect, [disconnect]);

  return { status, detections, sensorReadings, connect, disconnect };
}