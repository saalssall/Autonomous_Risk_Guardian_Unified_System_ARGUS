import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

// Plots this node's real risk_score history from the risk engine. No future
// projection line — the backend doesn't compute one, and fusion.py's
// hardcoded example numbers aren't a real calculation.
export function RiskEvolutionChart({ riskHistory }) {
  const data = riskHistory.map((entry) => ({
    time: new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    score: entry.risk_score,
    level: entry.risk_level,
  }));

  return (
    <div className="panel risk-chart-panel">
      <p className="eyebrow">Risk evolution</p>
      {data.length === 0 ? (
        <p className="empty-state">No risk history yet for this node.</p>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="var(--panel-border)" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="var(--text-dim)" fontSize={11} tickLine={false} />
            <YAxis domain={[0, 100]} stroke="var(--text-dim)" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "var(--panel)", border: "1px solid var(--panel-border)", borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: "var(--text-dim)" }}
              formatter={(value, _name, props) => [`${value}% (${props.payload.level})`, "Risk"]}
            />
            <Line type="monotone" dataKey="score" stroke="var(--alert)" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
