import { useState } from "react";
import { Header } from "./components/Header";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { CameraFeed } from "./components/CameraFeed";
import { DetectionLog } from "./components/DetectionLog";
import { SensorPanel } from "./components/SensorPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import "./App.css";

// Camera feed and detections currently come from separate sources (an MJPEG
// stream URL and a WebSocket). If the rover serves both from one host, this
// is a natural place to derive the stream URL from the WebSocket URL instead.
function streamUrlFor(status, roverUrl) {
  if (status !== "open" || !roverUrl) return null;
  return roverUrl.replace(/^ws/, "http").replace(/:\d+$/, ":8080/stream");
}

export default function App() {
  const { status, detections, sensorReadings, connect } = useWebSocket();
  const [roverUrl, setRoverUrl] = useState("");

  function handleConnect(url) {
    setRoverUrl(url);
    connect(url);
  }

  return (
    <div className="app">
      <Header status={status} />
      <main className="grid">
        <ConnectionPanel status={status} onConnect={handleConnect} />
        <CameraFeed streamUrl={streamUrlFor(status, roverUrl)} />
        <SensorPanel readings={sensorReadings} />
        <DetectionLog detections={detections} />
      </main>
    </div>
  );
}
