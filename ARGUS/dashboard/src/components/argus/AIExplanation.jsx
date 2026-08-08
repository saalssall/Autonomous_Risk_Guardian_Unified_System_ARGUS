export function AIExplanation({ latestRisk }) {
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
        </>
      )}
    </div>
  );
}
