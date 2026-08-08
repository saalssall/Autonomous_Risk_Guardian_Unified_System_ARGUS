import { useState } from "react";

export function ConnectionPanel({ status, onConnect }) {
  const [url, setUrl] = useState("ws://localhost:8765");
  const [token, setToken] = useState("");
  const [validationError, setValidationError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();

    try {
      const endpoint = new URL(url.trim());
      const isLocal = ["localhost", "127.0.0.1", "::1"].includes(
        endpoint.hostname
      );

      if (!["ws:", "wss:"].includes(endpoint.protocol)) {
        throw new Error("Use a ws:// or wss:// address.");
      }

      if (
        window.location.protocol === "https:" &&
        endpoint.protocol !== "wss:" &&
        !isLocal
      ) {
        throw new Error("Use wss:// when this dashboard is served over HTTPS.");
      }

      if (!token.trim()) {
        throw new Error("Enter the ARGUS access token.");
      }

      sessionStorage.setItem("argusAccessToken", token.trim());
      setValidationError("");
      onConnect(endpoint.toString(), token.trim());
    } catch (error) {
      setValidationError(
        error.message || "Enter a valid server address."
      );
    }
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
          placeholder="ws://localhost:8765"
        />

        <input
          id="access-token"
          type="password"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="ARGUS access token"
          autoComplete="current-password"
          aria-label="ARGUS access token"
        />

        <button
          type="submit"
          disabled={status === "connecting" || status === "authenticating"}
        >
          {status === "authenticating"
            ? "Authenticating…"
            : status === "open"
              ? "Reconnect"
              : "Connect"}
        </button>
      </div>

      {validationError && (
        <p role="alert" className="connection-error">
          {validationError}
        </p>
      )}
    </form>
  );
}