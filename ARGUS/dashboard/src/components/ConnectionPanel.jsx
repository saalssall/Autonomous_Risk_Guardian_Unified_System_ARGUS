import { useState } from "react";

// No token field here — unlike the authenticated WebSocket server, this
// FastAPI backend has no auth on any endpoint. If that matters before the
// demo, it needs adding on the backend first; nothing to configure here.
export function ConnectionPanel({ status, onConnect }) {
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [nodeId, setNodeId] = useState("ARGUS-01");

  function handleSubmit(event) {
    event.preventDefault();
    if (backendUrl.trim() && nodeId.trim()) {
      onConnect(backendUrl.trim(), nodeId.trim());
    }
  }

  return (
    <form className="panel connection-panel" onSubmit={handleSubmit}>
      <label htmlFor="backend-url">Backend address</label>
      <div className="connection-row">
        <input
          id="backend-url"
          type="text"
          value={backendUrl}
          onChange={(event) => setBackendUrl(event.target.value)}
          placeholder="http://localhost:8000"
        />
        <input
          id="node-id"
          type="text"
          value={nodeId}
          onChange={(event) => setNodeId(event.target.value)}
          placeholder="Node ID"
          aria-label="Node ID"
        />
        <button type="submit" disabled={status === "connecting"}>
          {status === "open" ? "Refresh" : "Connect"}
        </button>
      </div>
    </form>
  );
}
