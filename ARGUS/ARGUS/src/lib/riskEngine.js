/**
 * ARGUS Risk Engine
 * ------------------
 * Framework-agnostic risk assessment logic. Pure functions, no React/DOM
 * dependencies, so it can run in the dashboard today and move onto a real
 * backend (FastAPI risk-assessment service) later without a rewrite.
 *
 * Implements the rules from the ARGUS blueprint:
 *  - 5-tier risk enum (LOW / GUARDED / ELEVATED / HIGH / CRITICAL)
 *  - No hardcoded absolute triggers — risk is relative to a rolling baseline,
 *    rate of change, spatial corroboration, and external inputs
 *  - Environmental risk is fully decoupled from device health
 *
 * Honesty note: the "projection" below is a simple linear extrapolation of
 * the current anomaly trend, not a real forecasting model. It's labeled as
 * such in the output — don't oversell it in the pitch.
 */

export const RISK_LEVELS = ["LOW", "GUARDED", "ELEVATED", "HIGH", "CRITICAL"];

export const DEVICE_HEALTH_STATES = ["HEALTHY", "DEGRADED", "OFFLINE"];

// Metrics we track a rolling baseline for, and how much each one
// contributes to the overall anomaly score. Tune these once you have real
// sensor behavior to look at — these are reasonable hackathon defaults.
const TRACKED_METRICS = {
  temperature: { weight: 1.0 },
  humidity: { weight: 0.6 },
  distance_cm: { weight: 1.2 }, // falling distance can mean rising water level
  sound_level: { weight: 0.5 },
};

const MIN_BASELINE_SAMPLES = 3; // need at least this many past readings to trust a baseline
const STALE_READING_MS = 60_000; // no reading in 60s → treat node as offline

function mean(values) {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function stddev(values, avg) {
  if (values.length < 2) return 0;
  const variance = mean(values.map((v) => (v - avg) ** 2));
  return Math.sqrt(variance);
}

/**
 * Computes baseline, delta, and rate of change for one metric given a
 * history of past readings (oldest → newest, NOT including `current`).
 * Returns null if there isn't enough history to trust a baseline yet.
 */
function computeMetricTrend(history, key, current, currentTimestampMs) {
  const values = history.map((r) => r[key]).filter((v) => typeof v === "number" && !Number.isNaN(v));
  if (values.length < MIN_BASELINE_SAMPLES || typeof current !== "number" || Number.isNaN(current)) {
    return null;
  }

  const baseline = mean(values);
  const std = stddev(values, baseline) || Math.max(Math.abs(baseline) * 0.05, 0.5); // avoid div-by-zero on flat data
  const delta = current - baseline;
  const percentDelta = baseline !== 0 ? (delta / baseline) * 100 : null;
  const zScore = delta / std;

  const oldestTimestamp = history[0]?.timestampMs ?? currentTimestampMs;
  const timeFrameMinutes = Math.max((currentTimestampMs - oldestTimestamp) / 60_000, 1 / 60);
  const ratePerMinute = delta / timeFrameMinutes;

  const STABLE_THRESHOLD_Z = 0.25;
  const direction = zScore > STABLE_THRESHOLD_Z ? "increasing" : zScore < -STABLE_THRESHOLD_Z ? "decreasing" : "stable";

  return {
    key,
    baseline,
    current,
    delta,
    percentDelta,
    zScore,
    ratePerMinute,
    direction,
    timeFrameMinutes,
  };
}

/**
 * Very lightweight heuristic hazard categorization based on which metrics
 * are trending and in what direction. This is intentionally simple — swap
 * in something smarter once you have the vision/weather signals wired up.
 */
function categorizeHazard(trends) {
  const t = Object.fromEntries(trends.filter(Boolean).map((tr) => [tr.key, tr]));

  const distanceFalling = t.distance_cm?.direction === "decreasing" && t.distance_cm.zScore < -1;
  const humidityRising = t.humidity?.direction === "increasing";
  const tempRisingFast = t.temperature?.direction === "increasing" && t.temperature.zScore > 1.5;
  const soundSpike = t.sound_level?.direction === "increasing" && t.sound_level.zScore > 2;

  if (distanceFalling && humidityRising) return "Flood Risk";
  if (tempRisingFast && !humidityRising) return "Fire Risk";
  if (soundSpike && distanceFalling) return "Structural Hazard";
  if (trends.some((tr) => tr && Math.abs(tr.zScore) > 1)) return "Environmental Anomaly";
  return "No Active Hazard";
}

/**
 * Device health is computed entirely separately from environmental risk —
 * per the spec, a HIGH temperature reading from a DEGRADED sensor should
 * never be presented as confidently as one from a HEALTHY sensor.
 */
export function assessDeviceHealth(reading, nowMs = Date.now()) {
  const faultReasons = [];

  const isStale = !reading || nowMs - reading.timestampMs > STALE_READING_MS;
  if (isStale) {
    return { status: "OFFLINE", faultReasons: ["No data received recently"] };
  }

  if (reading.beam_status === "broken") faultReasons.push("Enclosure beam broken");
  if (typeof reading.battery === "number" && reading.battery < 20) faultReasons.push("Battery depleted");
  if (typeof reading.device_health === "number" && reading.device_health < 50) {
    faultReasons.push("Multiple onboard sensor checks failing");
  }

  if (faultReasons.length === 0) return { status: "HEALTHY", faultReasons: [] };

  const status = typeof reading.device_health === "number" && reading.device_health < 25 ? "OFFLINE" : "DEGRADED";
  return { status, faultReasons };
}

/**
 * Main entry point. Give it:
 *  - history: array of past sensor readings for this node, oldest→newest,
 *             each shaped like { ...sensorFields, timestampMs }
 *  - current: the latest sensor reading, same shape
 *  - options.corroboratingNodes: how many *other* nodes are currently
 *             showing an elevated reading (spatial verification)
 *  - options.weatherAlignment: bool | null — does external weather data
 *             support the hazard hypothesis? null = no data available
 *  - options.visionConfirmation: { label, confidence } | null — latest
 *             camera/vision-AI observation for this node, if any
 *
 * Returns a full RiskAssessment object matching Component C/D of the spec.
 */
export function assessRisk(history, current, options = {}) {
  const { corroboratingNodes = 0, weatherAlignment = null, visionConfirmation = null } = options;
  const nowMs = current?.timestampMs ?? Date.now();

  const deviceHealth = assessDeviceHealth(current, nowMs);

  // Degraded/offline hardware shouldn't drive a confident environmental
  // risk call — cap what the engine will report.
  const hardwareCapsConfidence = deviceHealth.status !== "HEALTHY";

  const trends = Object.keys(TRACKED_METRICS).map((key) =>
    computeMetricTrend(history, key, current?.[key], nowMs)
  );
  const validTrends = trends.filter(Boolean);

  if (validTrends.length === 0) {
    return {
      risk_level: "LOW",
      confidence: 0,
      hazard_category: "Insufficient Data",
      explanation: "Not enough historical readings yet to establish a baseline for this node.",
      trends: [],
      evidence: [],
      projection: null,
      device_health: deviceHealth,
    };
  }

  // Weighted anomaly score across tracked metrics.
  let weightedScore = 0;
  let weightTotal = 0;
  validTrends.forEach((trend) => {
    const weight = TRACKED_METRICS[trend.key].weight;
    weightedScore += Math.min(Math.abs(trend.zScore), 4) * weight; // clamp outliers
    weightTotal += weight;
  });
  const anomalyScore = weightTotal > 0 ? weightedScore / weightTotal / 4 : 0; // normalize to ~0-1

  // Evidence checklist — each true item both explains the call and nudges
  // confidence/severity up, per the spec's "cross-verified evidence" rule.
  const evidence = [
    { label: `${corroboratingNodes} nearby node${corroboratingNodes === 1 ? "" : "s"} corroborate`, met: corroboratingNodes > 0 },
    { label: "Rapid rate of environmental change", met: validTrends.some((t) => Math.abs(t.zScore) > 1.5) },
    { label: "External weather data alignment", met: weatherAlignment === true },
    { label: "Visual AI confirmation", met: !!visionConfirmation && visionConfirmation.confidence >= 0.6 },
  ];
  const evidenceMetCount = evidence.filter((e) => e.met).length;

  // Combine anomaly score with evidence into a final 0-1 severity score.
  let severity = anomalyScore;
  severity += evidenceMetCount * 0.08; // each corroborating signal nudges severity up
  severity = Math.min(severity, 1);

  const risk_level =
    severity >= 0.85 ? "CRITICAL" :
    severity >= 0.65 ? "HIGH" :
    severity >= 0.45 ? "ELEVATED" :
    severity >= 0.25 ? "GUARDED" :
    "LOW";

  // Confidence reflects how much evidence backs the call, capped low if
  // hardware is degraded — never let a flaky sensor look authoritative.
  let confidence = 0.4 + evidenceMetCount * 0.12 + Math.min(validTrends.length / Object.keys(TRACKED_METRICS).length, 1) * 0.15;
  confidence = Math.min(confidence, hardwareCapsConfidence ? 0.5 : 0.97);

  const hazard_category = categorizeHazard(validTrends);

  const explanation = buildExplanation(risk_level, hazard_category, validTrends, evidence, deviceHealth);

  const projection = buildProjection(severity, validTrends);

  return {
    risk_level,
    confidence: Math.round(confidence * 100) / 100,
    hazard_category,
    explanation,
    trends: validTrends.map((t) => ({
      key: t.key,
      direction: t.direction,
      timeFrameMinutes: Math.round(t.timeFrameMinutes),
      absoluteDelta: Math.round(t.delta * 10) / 10,
      percentDelta: t.percentDelta != null ? Math.round(t.percentDelta * 10) / 10 : null,
    })),
    evidence,
    projection,
    device_health: deviceHealth,
  };
}

function buildExplanation(riskLevel, hazardCategory, trends, evidence, deviceHealth) {
  if (deviceHealth.status !== "HEALTHY") {
    return `Node hardware is ${deviceHealth.status.toLowerCase()} (${deviceHealth.faultReasons.join(", ")}). Environmental risk reported with reduced confidence until sensor integrity is restored.`;
  }
  const strongest = [...trends].sort((a, b) => Math.abs(b.zScore) - Math.abs(a.zScore))[0];
  const metCount = evidence.filter((e) => e.met).length;
  if (riskLevel === "LOW") {
    return "All tracked metrics are within their recent normal range for this node.";
  }
  return `${strongest.key.replace("_", " ")} is ${strongest.direction} relative to this node's recent baseline` +
    `${strongest.percentDelta != null ? ` (${strongest.percentDelta > 0 ? "+" : ""}${Math.round(strongest.percentDelta)}%)` : ""}, ` +
    `consistent with ${hazardCategory.toLowerCase()}. ${metCount} of ${evidence.length} corroborating signals are present.`;
}

/**
 * Naive linear extrapolation of the current severity trend into the future.
 * This is NOT a forecast model — it just projects "if this rate of change
 * continues" so the dashboard has something to show for Component C's
 * Now/+30m/+60m/+90m row. Label it as a projection, not a prediction.
 */
function buildProjection(currentSeverity, trends) {
  const avgRatePerMinute = mean(trends.map((t) => Math.abs(t.zScore) / Math.max(t.timeFrameMinutes, 1)));
  const growthPerStep = Math.min(avgRatePerMinute * 30, 0.25); // cap so it doesn't blow up unrealistically

  const toPercent = (s) => Math.round(Math.min(Math.max(s, 0), 1) * 100);

  return {
    now: toPercent(currentSeverity),
    plus30m: toPercent(currentSeverity + growthPerStep),
    plus60m: toPercent(currentSeverity + growthPerStep * 2),
    plus90m: toPercent(currentSeverity + growthPerStep * 3),
    note: "Linear projection based on current rate of change — illustrative, not a forecast.",
  };
}
