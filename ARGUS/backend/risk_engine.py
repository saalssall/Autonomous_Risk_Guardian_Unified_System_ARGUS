"""
ARGUS risk engine — Person 2's math, implemented.

For each new sensor reading, computes a real per-node risk assessment:
  1. OBSERVATION — the raw reading itself (already stored by main.py)
  2. ANOMALY — how far each measurement is from this node's own recent
     baseline (rolling mean/std over its last N readings), as a z-score
  3. RISK — the anomaly scores combined with a rate-of-change signal, a
     spatial-agreement signal (do other nodes show similar deviation), and
     a historical-similarity signal (has this node been high-risk under
     similar conditions before) — weighted per argus_config.json, then
     bucketed into a risk_level via the same config
  4. CONFIDENCE — how much history this assessment is actually resting on

This deliberately does NOT call a raw measurement itself "high risk" — see
argus_config.json's risk_weights for exactly how much each factor counts.
"""
import json
import math
import os

import database

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "argus_config.json")
BASELINE_WINDOW = 10  # how many previous readings to use for the rolling baseline
EPSILON = 1e-6  # avoids divide-by-zero when a sensor's readings haven't varied yet

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)


def _zscore(value, history_values):
    """How many standard deviations `value` is from the mean of history_values."""
    if len(history_values) < 2:
        return 0.0  # not enough history to say anything is anomalous yet
    mean = sum(history_values) / len(history_values)
    variance = sum((x - mean) ** 2 for x in history_values) / len(history_values)
    std = math.sqrt(variance)
    # A fixed tiny epsilon still blows up when std is genuinely ~0 (a sensor
    # that hasn't varied at all yet) — scale it against the value itself so
    # a real but small deviation doesn't read as hundreds of standard
    # deviations.
    denominator = std + max(EPSILON, abs(mean) * 0.01)
    return (value - mean) / denominator


def _squash(z):
    """Maps an absolute z-score onto 0-1 — a z of 3+ (very unusual) maxes out."""
    return min(abs(z) / 3.0, 1.0)


def _bucket_risk_level(score):
    for level, (low, high) in CONFIG["risk_levels"].items():
        if low <= score <= high:
            return level
    return "CRITICAL" if score > 100 else "LOW"


def _rate_of_change_score(current, previous, history_values):
    """Normalizes how fast a value is moving against its own historical spread."""
    if previous is None or len(history_values) < 2:
        return 0.0
    std = math.sqrt(sum((x - sum(history_values) / len(history_values)) ** 2 for x in history_values) / len(history_values))
    delta = current - previous
    return min(abs(delta) / (std + EPSILON) / 3.0, 1.0)


def _spatial_agreement(db, node_id, current_z_scores):
    """Do OTHER nodes' most recent readings show similarly unusual deviation?
    Agreement here means 'other nodes are also anomalous', not 'equal values'.
    Returns 0-1; 0 if there's no other node data yet to compare against."""
    other_nodes = db.query(database.NodeModel).filter(database.NodeModel.node_id != node_id).all()
    if not other_nodes:
        return 0.0

    agreement_scores = []
    for other in other_nodes:
        recent = db.query(database.SensorReadingModel)\
            .filter(database.SensorReadingModel.node_id == other.node_id)\
            .order_by(database.SensorReadingModel.timestamp.desc())\
            .limit(BASELINE_WINDOW + 1).all()
        if len(recent) < 3:
            continue
        latest, history = recent[0], [r.temperature for r in recent[1:]]
        other_temp_z = _squash(_zscore(latest.temperature, history))
        agreement_scores.append(other_temp_z)

    if not agreement_scores:
        return 0.0
    avg_other_anomaly = sum(agreement_scores) / len(agreement_scores)
    own_anomaly = _squash(current_z_scores.get("temperature", 0))
    # High agreement = both this node AND others are anomalous together.
    return min(avg_other_anomaly, own_anomaly)


def _historical_similarity(db, node_id):
    """Simple frequency-based proxy: what fraction of this node's past
    assessments were HIGH or CRITICAL? A real similarity model (comparing
    the actual anomaly vector to past high-risk vectors) would be a
    meaningful upgrade here if there's time — this is the fast version."""
    past = db.query(database.RiskAssessmentModel)\
        .filter(database.RiskAssessmentModel.node_id == node_id).all()
    if not past:
        return 0.0
    high_risk_count = sum(1 for r in past if r.risk_level in ("HIGH", "CRITICAL"))
    return high_risk_count / len(past)


def _infer_hazard(temp_z, humidity_z, distance_z, latest):
    """Best-guess hazard label from which signal is dominant. Deliberately
    coarse — a real classifier would use much more than three numbers."""
    if abs(distance_z) >= max(abs(temp_z), abs(humidity_z)) and latest.distance is not None and distance_z < -1:
        return "flood_or_obstruction"
    if temp_z > 1 and humidity_z < -0.5:
        return "fire"
    if latest.beam_status == "broken":
        return "intrusion_or_structural"
    return "environmental_anomaly"


def _build_explanation(readings_context, rate_score, spatial, historical):
    """Real, data-driven bullet points — describes actual values against
    baseline (not raw z-scores, which can blow up to nonsensical numbers
    when a sensor's recent readings have near-zero variance) and only
    mentions factors that are actually significant."""
    lines = []
    for name, unit, current, history, z in readings_context:
        if len(history) < 2 or abs(z) < 1:
            continue
        baseline = sum(history) / len(history)
        direction = "above" if current > baseline else "below"
        lines.append(f"{name} is {current:.1f}{unit}, {direction} its recent baseline of {baseline:.1f}{unit}.")
    if rate_score >= 0.5:
        lines.append("Conditions are changing rapidly compared to this node's recent history.")
    if spatial >= 0.5:
        lines.append("Nearby nodes are showing similar deviation.")
    if historical >= 0.3:
        lines.append("Conditions resemble this node's past high-risk observations.")
    if not lines:
        lines.append("No individual signal is significantly outside its recent baseline.")
    return " ".join(lines)


def _recommendation_for(risk_level):
    return {
        "LOW": "Continue routine monitoring.",
        "GUARDED": "Increase monitoring frequency for this node.",
        "ELEVATED": "Increase monitoring in the affected sector and review nearby nodes.",
        "HIGH": "Increase monitoring and prepare a local warning if conditions continue to deteriorate.",
        "CRITICAL": "Issue a warning for the affected sector and prepare evacuation guidance.",
    }.get(risk_level, "Continue routine monitoring.")


def compute_risk_assessment(db, node_id, latest_reading):
    """Computes and stores a new RiskAssessmentModel row for this node,
    based on its just-saved latest_reading and its recent history."""
    history = db.query(database.SensorReadingModel)\
        .filter(database.SensorReadingModel.node_id == node_id)\
        .filter(database.SensorReadingModel.id != latest_reading.id)\
        .order_by(database.SensorReadingModel.timestamp.desc())\
        .limit(BASELINE_WINDOW).all()

    temp_history = [r.temperature for r in history if r.temperature is not None]
    humidity_history = [r.humidity for r in history if r.humidity is not None]
    distance_history = [r.distance for r in history if r.distance is not None]

    temp_z = _zscore(latest_reading.temperature, temp_history)
    humidity_z = _zscore(latest_reading.humidity, humidity_history)
    distance_z = _zscore(latest_reading.distance, distance_history)

    previous = history[0] if history else None
    rate_score = max(
        _rate_of_change_score(latest_reading.temperature, previous.temperature if previous else None, temp_history),
        _rate_of_change_score(latest_reading.humidity, previous.humidity if previous else None, humidity_history),
        _rate_of_change_score(latest_reading.distance, previous.distance if previous else None, distance_history),
    )

    spatial = _spatial_agreement(db, node_id, {"temperature": temp_z, "humidity": humidity_z, "distance": distance_z})
    historical = _historical_similarity(db, node_id)

    weights = CONFIG["risk_weights"]
    combined = (
        weights["temperature"] * _squash(temp_z)
        + weights["humidity"] * _squash(humidity_z)
        + weights["distance"] * _squash(distance_z)
        + weights["rate_of_change"] * rate_score
        + weights["spatial"] * spatial
        + weights["historical"] * historical
    )
    risk_score = round(combined * 100, 1)
    risk_level = _bucket_risk_level(risk_score)

    confidence = round(min(len(history) / BASELINE_WINDOW, 1.0) * 100, 1)

    last_assessment = db.query(database.RiskAssessmentModel)\
        .filter(database.RiskAssessmentModel.node_id == node_id)\
        .order_by(database.RiskAssessmentModel.timestamp.desc()).first()
    trend = "steady"
    if last_assessment and last_assessment.risk_score is not None:
        delta = (risk_score - last_assessment.risk_score) / 100
        if delta >= CONFIG["trend_thresholds"]["increasing"]:
            trend = "increasing"
        elif delta <= CONFIG["trend_thresholds"]["decreasing"]:
            trend = "decreasing"

    assessment = database.RiskAssessmentModel(
        node_id=node_id,
        region=node_id,  # no separate region concept yet — one node, one region
        hazard=_infer_hazard(temp_z, humidity_z, distance_z, latest_reading),
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        trend=trend,
        explanation=_build_explanation(
            [
                ("Temperature", "°C", latest_reading.temperature, temp_history, temp_z),
                ("Humidity", "%", latest_reading.humidity, humidity_history, humidity_z),
                ("Distance", "cm", latest_reading.distance, distance_history, distance_z),
            ],
            rate_score, spatial, historical,
        ),
        recommendation=_recommendation_for(risk_level),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment
