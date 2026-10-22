"""
Core incident constants used across all services.
Every agency, every dashboard, every AI model uses these same values.
"""

# ── Hazard Types ──────────────────────────────────────────────
# Must match ERSS/112 incident types where applicable
class HazardType:
    FLOOD = "flood"
    LANDSLIDE = "landslide"
    EARTHQUAKE = "earthquake"
    CYCLONE = "cyclone"
    BUILDING_COLLAPSE = "building_collapse"
    FIRE = "fire"
    HAZMAT_CHEMICAL = "hazmat_chemical"
    HAZMAT_RADIOLOGICAL = "hazmat_radiological"
    HAZMAT_BIOLOGICAL = "hazmat_biological"
    FLASH_FLOOD = "flash_flood"
    CLOUDBURST = "cloudburst"
    AVALANCHE = "avalanche"
    STORM_SURGE = "storm_surge"
    TSUNAMI = "tsunami"
    DROUGHT = "drought"
    ROAD_ACCIDENT = "road_accident"  # from 1073
    RAIL_ACCIDENT = "rail_accident"  # from 139/RailMadad
    URBAN_FLOODING = "urban_flooding"
    INDUSTRIAL_ACCIDENT = "industrial_accident"
    GAS_LEAK = "gas_leak"  # from 1906

    ALL = [
        FLOOD, LANDSLIDE, EARTHQUAKE, CYCLONE, BUILDING_COLLAPSE,
        FIRE, HAZMAT_CHEMICAL, HAZMAT_RADIOLOGICAL, HAZMAT_BIOLOGICAL,
        FLASH_FLOOD, CLOUDBURST, AVALANCHE, STORM_SURGE, TSUNAMI,
        DROUGHT, ROAD_ACCIDENT, RAIL_ACCIDENT, URBAN_FLOODING,
        INDUSTRIAL_ACCIDENT, GAS_LEAK,
    ]


# ── Severity Levels ───────────────────────────────────────────
class Severity:
    CRITICAL = "critical"   # mass casualty, imminent life loss
    HIGH = "high"           # significant life risk, multiple victims
    MODERATE = "moderate"   # contained but needs response
    LOW = "low"            # minor, monitoring only
    ADVISORY = "advisory"  # early-warning, no active incident

    ORDERED = [LOW, MODERATE, HIGH, CRITICAL]


# ── Incident Status ───────────────────────────────────────────
class IncidentStatus:
    RECEIVED = "received"            # just ingested
    AI_TRIAGING = "ai_triaing"       # AI is processing
    AI_TRIAGED = "ai_triaged"        # AI done, awaiting human review
    HUMAN_REVIEWING = "human_reviewing"  # SEOC officer is reviewing
    APPROVED = "approved"            # human approved AI recommendation
    OVERRIDDEN = "overridden"        # human changed AI recommendation
    SWARM_DISPATCHING = "swarm_dispatching"  # swarm teams notified
    SWARM_DEPLOYING = "swarm_deploying"      # Mother Drone launching
    AREA_SATURATION = "area_saturation"      # legions scanning
    RESCUE_IN_PROGRESS = "rescue_in_progress"
    RESCUE_CONFIRMED = "rescue_confirmed"    # manual confirmation per your doc
    CLOSING = "closing"
    CLOSED = "closed"
    ESCALATED_NDRF = "escalated_ndrf"        # escalated to national level


# ── Drone Types ───────────────────────────────────────────────
class DroneType:
    MOTHER = "mother"
    ANT = "ant"        # ground/rubble scout
    BEE = "bee"        # aerial scout
    MEDICAL = "medical"  # first-aid + telemedicine

    ALL = [MOTHER, ANT, BEE, MEDICAL]


# ── Legion Status ─────────────────────────────────────────────
class LegionStatus:
    IDLE = "idle"
    ASSIGNED = "assigned"
    DEPLOYING = "deploying"
    SCANNING = "scanning"
    TARGET_ACQUIRED = "target_acquired"
    RELAYING_INTEL = "relaying_intel"
    RECALLING = "recalling"
    DOCKED = "docked"


# ── Rescue Team Status ────────────────────────────────────────
class RescueTeamStatus:
    STANDBY = "standby"
    ASSIGNED_TARGET = "assigned_target"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    RESCUING = "rescuing"
    VICTIM_SECURED = "victim_secured"
    RETURNING = "returning"
    AVAILABLE = "available"


# ── Agency Codes ──────────────────────────────────────────────
class AgencyCode:
    SDMA = "sdma"
    SEOC = "seoc"
    NDRF = "ndrf"
    SDRF = "sdrf"
    FIRE = "fire"
    POLICE = "police"
    HEALTH_108 = "health_108"
    HEALTH_104 = "health_104"
    ERSS_112 = "erss_112"
    IMD = "imd"
    INCOIS = "incois"
    CWC = "cwc"
    RAILWAYS = "railways"
    MHA_NERC = "mha_nerc"
    NDMA = "ndma"


# ── Kafka Topics ──────────────────────────────────────────────
class KafkaTopic:
    INCIDENT_CREATED = "incident.created"
    INCIDENT_UPDATED = "incident.updated"
    INCIDENT_AI_TRIAGED = "incident.ai_triaged"
    INCIDENT_HUMAN_REVIEWED = "incident.human_reviewed"
    INCIDENT_DISPATCHED = "incident.dispatched"
    INCIDENT_CLOSED = "incident.closed"

    DRONE_TELEMETRY = "drone.telemetry"
    DRONE_COMMAND = "drone.command"
    DRONE_STATUS = "drone.status"
    LEGION_UPDATE = "legion.update"

    RESCUE_ASSIGNMENT = "rescue.assignment"
    RESCUE_UPDATE = "rescue.update"
    RESCUE_CONFIRMATION = "rescue.confirmation"

    ADVISORY_IMD = "advisory.imd"
    ADVISORY_INCOIS = "advisory.incois"
    ADVISORY_CWC = "advisory.cwc"
    ADVISORY_SACHET = "advisory.sachet"

    ERSS_INCIDENT = "erss.incident"   # from 112/ERSS connector


# ── MQTT Topics (drone ↔ ground) ─────────────────────────────
class MQTTTopic:
    MOTHER_TELEMETRY = "swarm/{mission_id}/mother/{drone_id}/telemetry"
    MOTHER_COMMAND = "swarm/{mission_id}/mother/{drone_id}/command"
    LEGION_TELEMETRY = "swarm/{mission_id}/legion/{legion_id}/{drone_type}/{drone_id}/telemetry"
    LEGION_COMMAND = "swarm/{mission_id}/legion/{legion_id}/{drone_type}/{drone_id}/command"
    VICTOR_DETECTED = "swarm/{mission_id}/victim/detected"
    MISSION_STATUS = "swarm/{mission_id}/status"


# ── Zone Types (from your Phase 3) ────────────────────────────
class ZoneType:
    DISASTER_PRONE = "disaster_prone"    # active disaster area
    SAFE = "safe"                        # 500m-1000m from boundary
    STANDBY = "standby"                  # 1km from boundary
    STAGING = "staging"                  # command center setup area


# ── Supported Languages ───────────────────────────────────────
class Language:
    EN = "en"
    HI = "hi"   # Hindi
    AS = "as"   # Assamese
    BN = "bn"   # Bengali
    GU = "gu"   # Gujarati
    KN = "kn"   # Kannada
    ML = "ml"   # Malayalam
    MR = "mr"   # Marathi
    OR = "or"   # Odia
    PA = "pa"   # Punjabi
    TA = "ta"   # Tamil
    TE = "te"   # Telugu
    UR = "ur"   # Urdu

    ALL = [EN, HI, AS, BN, GU, KN, ML, MR, OR, PA, TA, TE, UR]


# ── Time SLAs (seconds) ──────────────────────────────────────
class SLA:
    AI_TRIAGE_MAX = 30          # AI must triage within 30s
    HUMAN_REVIEW_MAX = 120      # Human must review within 2 min (auto-approve if exceeded)
    SWARM_DISPATCH_MAX = 300    # Swarm team notified within 5 min
    MOTHER_DRONE_LAUNCH_MAX = 600  # Mother Drone airborne within 10 min of dispatch
    RESCUE_CONFIRMATION_TIMEOUT = 1800  # 30 min timeout for manual confirmation
