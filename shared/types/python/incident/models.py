"""
SC&C Incident Schema - Shared Type Definitions
===============================================

This is the canonical incident schema used across all services.
Any changes must go through architecture review as they affect
S1 (creates), S2 (reviews), S3 (dispatches swarms), S4 (coordinates teams),
S5 (triggers from warnings), S6 (syncs with ERSS), S7 (exports to NDMIS).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IncidentChannel(str, Enum):
    """All intake channels for incident creation."""
    ERSS_112 = "erss_112"          # ERSS/112 PSAP
    CITIZEN_APP = "citizen_app"    # S10 Citizen App
    SMS = "sms"                    # SMS to shortcode
    WEB_FORM = "web_form"          # Web portal
    API_PARTNER = "api_partner"    # Partner API (SDRF, Fire, etc.)
    SOCIAL_MEDIA = "social_media"  # Twitter, WhatsApp Business API
    IOT_SENSOR = "iot_sensor"      # IoT flood/earthquake sensors
    EARLY_WARNING = "early_warning"  # S5 automated from IMD/INCOIS/CWC
    OFFICER_REPORT = "officer_report"  # Field officer direct report


class IncidentStatus(str, Enum):
    """Incident lifecycle states."""
    CREATED = "created"
    AI_TRIAGED = "ai_triaged"
    PENDING_REVIEW = "pending_review"      # In S2 review queue
    APPROVED = "approved"                   # Duty Officer approved
    REJECTED = "rejected"                   # Duty Officer rejected/merged
    DISPATCHING = "dispatching"             # Swarm/team being deployed
    ACTIVE = "active"                       # Operations in progress
    MONITORING = "monitoring"              # Ops complete, monitoring
    CLOSING = "closing"
    CLOSED = "closed"
    ARCHIVED = "archived"


class HazardType(str, Enum):
    """India-specific disaster taxonomy (NDMA classification)."""
    FLOOD = "flood"
    CYCLONE = "cyclone"
    EARTHQUAKE = "earthquake"
    LANDSLIDE = "landslide"
    CLOUDBURST = "cloudburst"
    AVALANCHE = "avalanche"
    DROUGHT = "drought"
    TSUNAMI = "tsunami"
    FIRE = "fire"                      # Urban/forest fire
    INDUSTRIAL = "industrial"          # Chemical/industrial accident
    EPIDEMIC = "epidemic"
    STAMPede = "stampede"
    BUILDING_COLLAPSE = "building_collapse"
    ROAD_ACCIDENT_MASS = "road_accident_mass"  # Mass casualty
    OTHER = "other"


class Severity(str, Enum):
    CRITICAL = "critical"    # Immediate life threat, swarm + NDRF
    HIGH = "high"            # Significant threat, swarm + SDRF
    MEDIUM = "medium"        # Moderate threat, SDRF + local
    LOW = "low"              # Minor, local response
    INFORMATIONAL = "informational"  # No dispatch needed


class SwarmLegionType(str, Enum):
    ANT = "ant"          # Search & mapping drones
    BEE = "bee"          # Communication relay drones
    MEDICAL = "medical"  # Medical supply delivery drones


class SwarmConfig(BaseModel):
    """Swarm deployment configuration."""
    mother_drone_count: int = Field(default=1, ge=1, le=5)
    ant_drones: int = Field(default=0, ge=0)
    bee_drones: int = Field(default=0, ge=0)
    medical_drones: int = Field(default=0, ge=0)
    formation_pattern: str = Field(default="adaptive")
    altitude_range_m: tuple[float, float] = Field(default=(30.0, 120.0))


class Incident(BaseModel):
    """Canonical incident record - the core data object of the system."""
    incident_id: str = Field(..., description="UUID v7 - time-ordered")
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    # Intake
    channel: IncidentChannel
    status: IncidentStatus = IncidentStatus.CREATED

    # Reporter
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    contact_consent: bool = False

    # Location (PostGIS in DB, Pydantic for API)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = None
    reverse_geocode: Optional[str] = None  # Auto-filled from PostGIS
    landmark: Optional[str] = None
    state: Optional[str] = None    # Auto-derived from geo
    district: Optional[str] = None  # Auto-derived from geo

    # Classification
    hazard_type: HazardType
    severity: Severity = Severity.MEDIUM
    estimated_scale: Optional[str] = None  # "village", "town", "city", "district"

    # Swarm decision
    needs_swarm: bool = False
    swarm_config: Optional[SwarmConfig] = None
    needs_human_team: bool = False
    human_team_requests: list[str] = Field(default_factory=list)  # ["NDRF", "SDRF", "Fire", "Medical"]

    # Media & Description
    media_urls: list[str] = Field(default_factory=list)  # MinIO URLs
    summary_text: Optional[str] = None

    # AI Triage
    ai_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_severity_prediction: Optional[Severity] = None
    ai_swarm_recommendation: Optional[SwarmConfig] = None

    # Human Review (S2)
    professional_reviewer_id: Optional[str] = None  # SEOC Duty Officer
    review_timestamp: Optional[datetime] = None
    review_decision: Optional[str] = None  # "approved", "rejected", "modified"
    override_notes: Optional[str] = None

    # External System IDs
    erss_incident_id: Optional[str] = None  # ERSS/112 reference
    ndmis_incident_id: Optional[str] = None  # NDMIS reference
    complaint_id: Optional[str] = None       # CPGRAMS reference

    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "0191a2b3-c4d5-7e8f-9a0b-1c2d3e4f5a6b",
                "channel": "citizen_app",
                "latitude": 30.3165,
                "longitude": 78.0320,
                "hazard_type": "landslide",
                "severity": "critical",
                "state": "Uttarakhand",
                "district": "Dehradun",
            }
        }
