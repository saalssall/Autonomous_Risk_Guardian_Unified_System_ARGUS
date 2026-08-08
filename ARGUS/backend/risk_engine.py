"""
ARGUS risk engine — Person 2's math, implemented.

For each new sensor reading (or camera observation), computes a real
per-node risk assessment:
  1. OBSERVATION — the raw reading itself (already stored by main.py)
  2. ANOMALY — how far each measurement is from this node's own recent
     baseline (rolling mean/std over its last N readings), as a z-score
  3. RISK — the anomaly scores combined with a rate-of-change signal, a
     spatial-agreement signal (do other nodes show similar deviation), a
     historical-similarity signal, and camera evidence if any — weighted
     per a DISASTER PROFILE selected from the inferred hazard (general/
     flood/heat — see argus_config.json's disaster_profiles), then bucketed
     into a risk_level via the same config
  4. CONFIDENCE — blends how much history this assessment rests on with
     how reliable the reporting device currently is

This deliberately does NOT call a raw measurement itself "high risk" — see
argus_config.json for exactly how much each factor counts, per profile.
"""
import datetime
import json
import math
import os

import database

CONFIG_PATH = os.environ.get(
    "ARGUS_CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "argus_config.json"),
)
BASELINE_WINDOW = 10  # how many previous readings to use for the rolling baseline
CAMERA_RELEVANCE_S = 300  # ignore camera detections older than this — a smoke
                          # sighting from an hour ago shouldn't keep inflating risk
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


def _real_rate_per_30min(current, previous_value, current_ts, previous_ts):
    """Real-units rate (e.g. °C per 30 min), for human display — separate
    from _rate_of_change_score above, which is normalized 0-1 for scoring.
    Returns None if there's nothing to compare against, or if the two
    readings are too close together in time to extrapolate a stable rate
    (dividing by a near-zero time delta blows the result up to nonsense —
    e.g. two readings 5ms apart implying millions of degrees per 30 min)."""
    if previous_value is None or previous_ts is None or current_ts is None:
        return None
    delta_minutes = (current_ts - previous_ts).total_seconds() / 60.0
    MIN_DELTA_MINUTES = 0.1  # ~6 seconds — below this, don't extrapolate
    if delta_minutes < MIN_DELTA_MINUTES:
        return None
    rate_per_minute = (current - previous_value) / delta_minutes
    return rate_per_minute * 30


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


def _camera_signal(db, node_id):
    """Most recent camera observation for this node, if any and if recent
    enough to still be relevant. Returns (score 0-1, list of flags that
    were true) — score is the observation's own confidence if any hazard
    flag (smoke/water/person/debris) was true, else (0.0, None)."""
    latest = db.query(database.CameraObservationModel)\
        .filter(database.CameraObservationModel.node_id == node_id)\
        .order_by(database.CameraObservationModel.timestamp.desc()).first()
    if latest is None:
        return 0.0, None
    age_seconds = (datetime.datetime.utcnow() - latest.timestamp).total_seconds()
    if age_seconds > CAMERA_RELEVANCE_S:
        return 0.0, None
    flags = [name for name in ("smoke", "water", "person", "debris") if getattr(latest, name)]
    if not flags:
        return 0.0, None
    return latest.confidence, flags


def _device_reliability(latest_reading):
    """Fraction (0-1) of the device-condition checks reporting healthy.
    Fields the sender never included (None) are excluded rather than
    counted as failures — a simulated node that doesn't report ir_beam_status
    at all shouldn't be penalized for a field it was never asked to send."""
    fields = [
        (latest_reading.esp32_online, True),
        (latest_reading.dht11_status, "OK"),
        (latest_reading.hcsr04_status, "OK"),
        (latest_reading.ir_beam_status, "OK"),
        (latest_reading.network_status, "CONNECTED"),
    ]
    known = [(actual, expected) for actual, expected in fields if actual is not None]
    if not known:
        return 1.0  # nothing reported — assume reliable rather than penalize confidence for it
    return sum(1 for actual, expected in known if actual == expected) / len(known)


def _infer_hazard(temp_z, humidity_z, distance_z, latest, camera_flags):
    """Best-guess hazard label. Camera evidence (direct visual confirmation)
    takes priority over the anomaly-based guess when available."""
    if camera_flags:
        if "smoke" in camera_flags:
            return "fire"
        if "water" in camera_flags:
            return "flood_or_obstruction"
        if "debris" in camera_flags:
            return "structural_damage"
        if "person" in camera_flags:
            return "person_detected"
    if abs(distance_z) >= max(abs(temp_z), abs(humidity_z)) and latest.distance is not None and distance_z < -1:
        return "flood_or_obstruction"
    if temp_z > 1 and humidity_z < -0.5:
        return "fire"
    if latest.beam_status == "broken":
        return "intrusion_or_structural"
    return "environmental_anomaly"


def _profile_for_hazard(hazard):
    """Maps the inferred hazard to a disaster profile — a different weight
    distribution per argus_config.json's disaster_profiles (e.g. flood
    conditions should weight the distance sensor much more heavily than a
    fire would). Falls back to "general" for anything not confidently
    categorized as a specific disaster type."""
    return {
        "flood_or_obstruction": "flood",
        "fire": "heat",
    }.get(hazard, "general")


def _build_explanation(readings_context, rate_score, spatial, historical, camera_flags, real_rates):
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
        line = f"{name} is {current:.1f}{unit}, {direction} its recent baseline of {baseline:.1f}{unit}."
        rate = real_rates.get(name)
        if rate is not None and abs(rate) >= 0.5:
            sign = "+" if rate > 0 else ""
            line += f" ({sign}{rate:.1f}{unit} / 30 min)"
        lines.append(line)
    if rate_score >= 0.5:
        lines.append("Conditions are changing rapidly compared to this node's recent history.")
    if spatial >= 0.5:
        lines.append("Nearby nodes are showing similar deviation.")
    if historical >= 0.3:
        lines.append("Conditions resemble this node's past high-risk observations.")
    if camera_flags:
        lines.append(f"Camera observed: {', '.join(camera_flags)}.")
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
    # For the real-units rate display, compare against the OLDEST reading in
    # the current window rather than just the immediately-previous one — at
    # a ~2s polling interval, two consecutive readings are almost always
    # under the 6s minimum delta in _real_rate_per_30min, so the display
    # would essentially never show up if compared to the immediate predecessor.
    oldest_in_window = history[-1] if history else None
    real_rates = {
        "Temperature": _real_rate_per_30min(latest_reading.temperature, oldest_in_window.temperature if oldest_in_window else None, latest_reading.timestamp, oldest_in_window.timestamp if oldest_in_window else None),
        "Humidity": _real_rate_per_30min(latest_reading.humidity, oldest_in_window.humidity if oldest_in_window else None, latest_reading.timestamp, oldest_in_window.timestamp if oldest_in_window else None),
        "Distance": _real_rate_per_30min(latest_reading.distance, oldest_in_window.distance if oldest_in_window else None, latest_reading.timestamp, oldest_in_window.timestamp if oldest_in_window else None),
    }

    spatial = _spatial_agreement(db, node_id, {"temperature": temp_z, "humidity": humidity_z, "distance": distance_z})
    historical = _historical_similarity(db, node_id)
    camera_score, camera_flags = _camera_signal(db, node_id)
    device_reliability = _device_reliability(latest_reading)

    hazard = _infer_hazard(temp_z, humidity_z, distance_z, latest_reading, camera_flags)
    profile_name = _profile_for_hazard(hazard)
    weights = CONFIG["disaster_profiles"][profile_name]

    # camera_weight is separate/additive rather than a slice of the profile's
    # 100% — the spec notes camera evidence "can initially be zero/omitted"
    # for teams without one, so it's treated as bonus evidence on top of the
    # core profile rather than something that shrinks the other weights.
    combined = (
        weights["temperature"] * _squash(temp_z)
        + weights["humidity"] * _squash(humidity_z)
        + weights["distance"] * _squash(distance_z)
        + weights["rate_of_change"] * rate_score
        + weights["spatial"] * spatial
        + weights["historical"] * historical
        + CONFIG.get("camera_weight", 0) * camera_score
    )
    risk_score = round(min(combined * 100, 100), 1)
    risk_level = _bucket_risk_level(risk_score)

    # Device reliability feeds CONFIDENCE, not risk_score. The spec's own
    # illustrative formula lists reliability alongside the other additive
    # risk terms, but taken literally that means a perfectly healthy device
    # (reliability=1.0) adds a flat risk floor even with zero anomalies —
    # a working sensor reporting normal readings shouldn't itself register
    # as "risky". The more defensible read is that reliability affects how
    # much to TRUST the assessment: a degraded sensor means less certainty
    # in whatever risk_score comes out, high or low.
    history_completeness = min(len(history) / BASELINE_WINDOW, 1.0)
    confidence = round((history_completeness * 0.6 + device_reliability * 0.4) * 100, 1)

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
        hazard=hazard,
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        trend=trend,
        disaster_profile=profile_name,
        explanation=_build_explanation(
            [
                ("Temperature", "°C", latest_reading.temperature, temp_history, temp_z),
                ("Humidity", "%", latest_reading.humidity, humidity_history, humidity_z),
                ("Distance", "cm", latest_reading.distance, distance_history, distance_z),
            ],
            rate_score, spatial, historical, camera_flags, real_rates,
        ),
        recommendation=_recommendation_for(risk_level),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment
