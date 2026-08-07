import { useCallback, useEffect, useRef, useState } from "react";

const MAX_DETECTIONS = 50; // cap so the log doesn't grow forever during a run

// Connects to the rover's WebSocket, tracks connection status, and collects
// incoming detection messages. Reconnecting is manual (call connect again)
// rather than automatic, since on a hackathon LAN the rover's IP can change.
export function useWebSocket() {
  const [status, setStatus] = useState("idle"); // idle | connecting | open | closed | error
  const [detections, setDetections] = useState([]);
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
        // Expecting JSON like: { label: "person", confidence: 0.87, timestamp: "..." }
        // Any message that fails to parse is ignored rather than crashing the log.
        try {
          const data = JSON.parse(event.data);
          setDetections((prev) => [{ ...data, id: crypto.randomUUID() }, ...prev].slice(0, MAX_DETECTIONS));
        } catch {
          // non-JSON message — skip it
        }
      };
    },
    [disconnect]
  );

  useEffect(() => disconnect, [disconnect]); // clean up socket on unmount

  return { status, detections, connect, disconnect };
}
