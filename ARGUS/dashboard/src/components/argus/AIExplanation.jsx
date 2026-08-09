import { useState } from "react";

export function AIExplanation({ latestRisk, backendUrl, nodeId }) {
  const [aiResult, setAiResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function fetchAiExplanation() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${backendUrl.replace(/\/$/, "")}/api/ai-explanation/${nodeId}`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      setAiResult(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel ai-explanation-panel">
      <p className="eyebrow">Why is risk changing?</p>
      {!latestRisk ? (
        <p className="empty-state">No assessment recorded yet.</p>
      ) : (
        <>
          <p className="ai-explanation-text">{latestRisk.explanation ?? "No explanation recorded for this assessment."}</p>
          <div className="ai-recommendation">
            <span className="eyebrow">Recommended action</span>
            <p>{latestRisk.recommendation}</p>
          </div>

          <div className="ai-llm-section">
            <button onClick={fetchAiExplanation} disabled={loading || !nodeId}>
              {loading ? "Asking Gemini…" : aiResult ? "Regenerate AI explanation" : "Get AI explanation"}
            </button>
            {error && <p className="connection-error">{error}</p>}
            {aiResult && (
              <div className="ai-llm-result">
                <span className="eyebrow">AI explanation (Gemini)</span>
                <p>{aiResult.summary}</p>
                <ul>
                  {aiResult.key_evidence.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
                <p className="ai-llm-action">
                  <strong>Recommended:</strong> {aiResult.recommended_action}
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
