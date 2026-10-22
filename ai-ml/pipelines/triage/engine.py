"""
S9 - AI Triage Pipeline
========================

Takes an incident and produces:
  - severity_score (0.0-1.0)
  - recommended_severity (critical/high/medium/low)
  - needs_swarm (bool)
  - swarm_config recommendation (drone counts)
  - confidence_score (0.0-1.0)

Models:
  - Text classifier: Fine-tuned BERT/IndicBERT for multilingual text
  - Feature model: XGBoost/LightGBM on structured features
  - Ensemble: Weighted combination of text + feature predictions

Human-in-the-loop: ALL predictions go to S2 review queue.
No automatic dispatch without Duty Officer approval.
"""

import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger("s9.triage")


class SeverityScore(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


# Hazard-specific swarm configurations
SWARM_PRESETS = {
    "flood": {"mother_drone_count": 2, "ant_drones": 12, "bee_drones": 4, "medical_drones": 6},
    "landslide": {"mother_drone_count": 1, "ant_drones": 8, "bee_drones": 2, "medical_drones": 4},
    "earthquake": {"mother_drone_count": 3, "ant_drones": 20, "bee_drones": 6, "medical_drones": 8},
    "cyclone": {"mother_drone_count": 2, "ant_drones": 16, "bee_drones": 6, "medical_drones": 6},
    "cloudburst": {"mother_drone_count": 1, "ant_drones": 8, "bee_drones": 3, "medical_drones": 4},
    "fire": {"mother_drone_count": 1, "ant_drones": 6, "bee_drones": 2, "medical_drones": 2},
    "tsunami": {"mother_drone_count": 2, "ant_drones": 16, "bee_drones": 6, "medical_drones": 10},
    "building_collapse": {"mother_drone_count": 2, "ant_drones": 12, "bee_drones": 3, "medical_drones": 6},
    "avalanche": {"mother_drone_count": 1, "ant_drones": 8, "bee_drones": 2, "medical_drones": 4},
    "industrial": {"mother_drone_count": 1, "ant_drones": 6, "bee_drones": 2, "medical_drones": 3},
    "epidemic": {"mother_drone_count": 1, "ant_drones": 4, "bee_drones": 2, "medical_drones": 8},
    "other": {"mother_drone_count": 1, "ant_drones": 6, "bee_drones": 2, "medical_drones": 2},
}

# Severity thresholds
SEVERITY_THRESHOLDS = {
    "critical": 0.85,
    "high": 0.65,
    "medium": 0.40,
    "low": 0.20,
}

# Keywords that boost severity
CRITICAL_KEYWORDS = [
    "trapped", "buried", "swept away", "collapsed", "stranded", "marooned",
    "drowning", "casualty", "fatalities", "death", "deaths", "critical",
    "life threat", "imminent danger", "flash flood", "dam break",
    # Hindi
    "फंसे", "दरकन", "बहा", "मृत्यु", "संकट",
]

HIGH_KEYWORDS = [
    "flooded", "landslide", "earthquake", "fire", "cyclone",
    "rescue needed", "injured", "hospital", "evacuation",
    # Hindi
    "बाढ़", "भूस्खलन", "भूकंप", "आग", "बचाव",
]


class TriageEngine:
    """
    AI triage engine — classifies incidents and recommends swarm deployment.

    Phase 1: Rule-based + keyword matching (fast, no ML model needed)
    Phase 2: Add XGBoost model for structured features
    Phase 3: Add fine-tuned BERT/IndicBERT for multilingual text
    """

    def __init__(self):
        self.model_version = "rule-v1"
        logger.info("Triage engine initialized (rule-based v1)")

    async def triage(self, incident: dict) -> dict:
        """
        Run AI triage on an incident.

        Returns severity, confidence, swarm recommendation.
        """
        text = (incident.get("summary_text") or "").lower()
        hazard = incident.get("hazard_type", "other")
        channel = incident.get("channel", "unknown")

        # Step 1: Keyword severity scoring
        keyword_score = self._keyword_severity(text)

        # Step 2: Channel priority (ERSS/112 > citizen app > social media)
        channel_score = self._channel_priority(channel)

        # Step 3: Hazard severity baseline
        hazard_score = self._hazard_baseline(hazard)

        # Step 4: Location risk (e.g., known landslide-prone area)
        location_score = self._location_risk(
            incident.get("state"), incident.get("district"), hazard
        )

        # Step 5: Time-of-day factor (night = higher risk)
        time_score = self._time_factor()

        # Ensemble: weighted combination
        raw_score = (
            keyword_score * 0.35 +
            channel_score * 0.15 +
            hazard_score * 0.25 +
            location_score * 0.15 +
            time_score * 0.10
        )

        # Determine severity
        severity = self._score_to_severity(raw_score)

        # Confidence based on text richness and source reliability
        confidence = self._calculate_confidence(incident, keyword_score)

        # Swarm recommendation
        needs_swarm = severity in ("critical", "high") and hazard in SWARM_PRESETS
        swarm_config = SWARM_PRESETS.get(hazard, SWARM_PRESETS["other"]) if needs_swarm else None

        # Scale swarm based on severity
        if swarm_config and severity == "critical":
            swarm_config = {k: int(v * 1.5) for k, v in swarm_config.items()}

        result = {
            "incident_id": incident.get("incident_id"),
            "ai_severity_prediction": severity,
            "ai_confidence_score": round(confidence, 3),
            "ai_raw_score": round(raw_score, 4),
            "needs_swarm": needs_swarm,
            "ai_swarm_recommendation": swarm_config,
            "needs_human_team": severity in ("critical", "high"),
            "human_team_requests": self._recommend_teams(severity, hazard),
            "model_version": self.model_version,
            "score_breakdown": {
                "keyword": round(keyword_score, 3),
                "channel": round(channel_score, 3),
                "hazard": round(hazard_score, 3),
                "location": round(location_score, 3),
                "time": round(time_score, 3),
            },
            "triaged_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Triage: {incident.get('incident_id', '?')} → {severity} "
            f"(confidence: {confidence:.2f}, swarm: {needs_swarm})"
        )
        return result

    def _keyword_severity(self, text: str) -> float:
        """Score severity based on keywords in description."""
        for kw in CRITICAL_KEYWORDS:
            if kw in text:
                return 0.95
        for kw in HIGH_KEYWORDS:
            if kw in text:
                return 0.75
        if len(text) > 50:
            return 0.50
        if len(text) > 10:
            return 0.35
        return 0.25

    def _channel_priority(self, channel: str) -> float:
        """Higher trust for official channels."""
        mapping = {
            "erss_112": 0.90, "ndrf": 0.90, "ndma": 0.85,
            "early_warning": 0.85, "imd": 0.85, "incois": 0.85, "cwc": 0.85, "sachet": 0.85,
            "officer_report": 0.80, "fire_101": 0.80, "police_100": 0.80, "ambulance_108": 0.80,
            "citizen_app": 0.60, "sms_shortcode": 0.55, "whatsapp_business": 0.50,
            "web_portal": 0.50, "social_media": 0.35, "iot_sensor": 0.70,
        }
        return mapping.get(channel, 0.40)

    def _hazard_baseline(self, hazard: str) -> float:
        """Baseline severity for different hazard types."""
        mapping = {
            "earthquake": 0.80, "tsunami": 0.95, "cyclone": 0.80,
            "flood": 0.70, "landslide": 0.75, "cloudburst": 0.85,
            "avalanche": 0.70, "fire": 0.60, "building_collapse": 0.75,
            "industrial": 0.65, "epidemic": 0.55, "drought": 0.30,
            "stampede": 0.60, "road_accident_mass": 0.55, "other": 0.35,
        }
        return mapping.get(hazard, 0.35)

    def _location_risk(self, state: str, district: str, hazard: str) -> float:
        """Location-specific risk adjustments."""
        # Known high-risk combinations
        high_risk = {
            ("Uttarakhand", "landslide"): 0.85,
            ("Uttarakhand", "earthquake"): 0.75,
            ("Kerala", "landslide"): 0.80,
            ("Kerala", "flood"): 0.80,
            ("Assam", "flood"): 0.85,
            ("Himachal Pradesh", "landslide"): 0.80,
            ("Tamil Nadu", "cyclone"): 0.75,
        }
        key = (state, hazard) if state else None
        return high_risk.get(key, 0.45)

    def _time_factor(self) -> float:
        """Night operations are higher risk."""
        hour = datetime.now(timezone.utc).hour
        # IST = UTC+5:30
        ist_hour = (hour + 5) % 24
        if 20 <= ist_hour or ist_hour <= 5:  # Night
            return 0.65
        elif 6 <= ist_hour <= 8 or 17 <= ist_hour <= 19:  # Twilight
            return 0.50
        return 0.40  # Day

    def _score_to_severity(self, score: float) -> str:
        if score >= SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif score >= SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif score >= SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        elif score >= SEVERITY_THRESHOLDS["low"]:
            return "low"
        return "informational"

    def _calculate_confidence(self, incident: dict, keyword_score: float) -> float:
        """Calculate confidence based on available information."""
        factors = []
        if incident.get("latitude") and incident.get("longitude"):
            factors.append(0.3)
        if incident.get("summary_text") and len(incident["summary_text"]) > 20:
            factors.append(0.25)
        if incident.get("hazard_type") and incident["hazard_type"] != "other":
            factors.append(0.2)
        if incident.get("reporter_phone"):
            factors.append(0.1)
        if keyword_score > 0.7:
            factors.append(0.15)

        base = sum(factors)
        return min(0.95, max(0.15, base))  # Clamp between 0.15 and 0.95

    def _recommend_teams(self, severity: str, hazard: str) -> list[str]:
        """Recommend human rescue teams based on severity and hazard."""
        if severity not in ("critical", "high"):
            return []

        teams = []
        if severity == "critical":
            teams.append("NDRF")
        teams.append("SDRF")

        if hazard in ("fire", "industrial"):
            teams.append("Fire")
        if hazard in ("flood", "cyclone", "tsunami"):
            teams.extend(["Navy", "Coast Guard"])
        if severity == "critical":
            teams.append("Health")  # NHM ambulance + hospitals

        return teams


# Singleton
triage_engine = TriageEngine()
