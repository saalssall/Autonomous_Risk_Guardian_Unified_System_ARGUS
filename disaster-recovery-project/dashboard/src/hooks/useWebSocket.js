import { useCallback, useEffect, useRef, useState } from "react";

const MAX_DETECTIONS = 50; // cap so the log doesn't grow forever during a run

// Connects to the Pi's WebSocket, tracks connection status, and routes
// incoming messages by their `type` field: "detection" events accumulate
// into a log, "sensor" readings just overwrite the latest snapshot.
// Reconnecting is manual (call connect again), since on a hackathon LAN the
// Pi's IP can change between runs.
export function useWebSocket() {
  const [status, setStatus] = useState("idle"); // idle | connecting | open | closed | error
  const [detections, setDetections] = useState([]);
  const [sensorReadings, setSensorReadings] = useState(null);
  const socketRef = useRef(null);

  const disconnect = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
  }, []);

  const connect = useCallback(
    (url) => {
      disconnect();
      setStatus("connecting");

      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => setStatus("open");
      socket.onclose = () => setStatus("closed");
      socket.onerror = () => setStatus("error");

      socket.onmessage = (event) => {
        // Any message that fails to parse, or has no recognised type, is
        // ignored rather than crashing the dashboard.
        try {
          const data = JSON.parse(event.data);
          if (data.type === "sensor") {
            setSensorReadings(data);
          } else if (data.type === "detection") {
            setDetections((prev) => [{ ...data, id: crypto.randomUUID() }, ...prev].slice(0, MAX_DETECTIONS));
          }
        } catch {
          // non-JSON message — skip it
        }
      };
    },
    [disconnect]
  );

  useEffect(() => disconnect, [disconnect]); // clean up socket on unmount

  return { status, detections, sensorReadings, connect, disconnect };
}
