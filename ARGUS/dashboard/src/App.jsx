import { ArgusHeader } from "./components/argus/ArgusHeader";
import { NodeMap } from "./components/argus/NodeMap";
import { NodePanel } from "./components/argus/NodePanel";
import { SensorCards } from "./components/argus/SensorCards";
import { RiskEvolutionChart } from "./components/argus/RiskEvolutionChart";
import { AIExplanation } from "./components/argus/AIExplanation";
import { DeviceHealthPanel } from "./components/argus/DeviceHealthPanel";
import { CameraObservationPanel } from "./components/argus/CameraObservationPanel";
import { useAuthorityData } from "./hooks/useAuthorityData";
import "./App.css";

const BACKEND_URL = "http://localhost:8000"; // change if the backend runs elsewhere

export default function App() {
  const {
    status, nodes, alerts,
    selectedNodeId, setSelectedNodeId, selectedNode,
    nodeRiskHistory, latestRisk,
    latestReading, previousReading, latestObservation, deviceHealth,
  } = useAuthorityData(BACKEND_URL);

  return (
    <div className="app">
      <ArgusHeader status={status} nodes={nodes} alerts={alerts} />
      <main className="argus-grid">
        <NodeMap nodes={nodes} selectedNodeId={selectedNodeId} onSelect={setSelectedNodeId} />
        <NodePanel node={selectedNode} latestRisk={latestRisk} />
        <SensorCards latestReading={latestReading} previousReading={previousReading} />
        <RiskEvolutionChart riskHistory={nodeRiskHistory} />
        <AIExplanation latestRisk={latestRisk} />
        <DeviceHealthPanel deviceHealth={deviceHealth} hasSelection={!!selectedNode} />
        <CameraObservationPanel observation={latestObservation} backendUrl={BACKEND_URL} />
      </main>
    </div>
  );
}
