import { Header } from "./components/Header";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { CameraFeed } from "./components/CameraFeed";
import { DetectionLog } from "./components/DetectionLog";
import { SensorPanel } from "./components/SensorPanel";
import { useBackendData } from "./hooks/useBackendData";
import "./App.css";

export default function App() {
  const { status, sensorReadings, detections, latestImageUrl, connect } = useBackendData();

  return (
    <div className="app">
      <Header status={status} />
      <main className="grid">
        <ConnectionPanel status={status} onConnect={connect} />
        <CameraFeed imageUrl={latestImageUrl} detection={detections[0]} />
        <SensorPanel readings={sensorReadings} />
        <DetectionLog detections={detections} />
      </main>
    </div>
  );
}
