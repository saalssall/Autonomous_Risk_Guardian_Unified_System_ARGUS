import { Link } from "react-router-dom";
import { ArgusHeader } from "../components/argus/ArgusHeader";
import { NodeMap } from "../components/argus/NodeMap";
import { NodePanel } from "../components/argus/NodePanel";
import { SensorCards } from "../components/argus/SensorCards";
import { RiskEvolutionChart } from "../components/argus/RiskEvolutionChart";
import { AIExplanation } from "../components/argus/AIExplanation";
import { DeviceHealthPanel } from "../components/argus/DeviceHealthPanel";
import { CameraObservationPanel } from "../components/argus/CameraObservationPanel";
import { useAuthorityData } from "../hooks/useAuthorityData";

export function AuthorityView({ backendUrl }) {
  const {
    status, nodes, alerts,
    selectedNodeId, setSelectedNodeId, selectedNode,
    nodeRiskHistory, latestRisk,
    latestReading, previousReading, latestObservation, deviceHealth,
  } = useAuthorityData(backendUrl);

  return (
    <div className="app">
      <div className="view-switch">
        <Link to="/resident">Switch to resident view →</Link>
      </div>
      <ArgusHeader status={status} nodes={nodes} alerts={alerts} />
      <main className="argus-grid">
        <NodeMap nodes={nodes} selectedNodeId={selectedNodeId} onSelect={setSelectedNodeId} />
        <NodePanel node={selectedNode} latestRisk={latestRisk} />
        <SensorCards latestReading={latestReading} previousReading={previousReading} />
        <RiskEvolutionChart riskHistory={nodeRiskHistory} />
        <AIExplanation latestRisk={latestRisk} backendUrl={backendUrl} nodeId={selectedNodeId} />
        <DeviceHealthPanel deviceHealth={deviceHealth} hasSelection={!!selectedNode} />
        <CameraObservationPanel observation={latestObservation} backendUrl={backendUrl} />
      </main>
    </div>
  );
}
