import { useState } from "react";

export function ConnectionPanel({ status, onConnect }) {
  const [url, setUrl] = useState("ws://raspberrypi.local:8765");

  function handleSubmit(event) {
    event.preventDefault();
    if (url.trim()) onConnect(url.trim());
  }

  return (
    <form className="panel connection-panel" onSubmit={handleSubmit}>
      <label htmlFor="rover-url">Rover address</label>
      <div className="connection-row">
        <input
          id="rover-url"
          type="text"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="ws://<rover-ip>:8765"
        />
        <button type="submit" disabled={status === "connecting"}>
          {status === "open" ? "Reconnect" : "Connect"}
        </button>
      </div>
    </form>
  );
}
