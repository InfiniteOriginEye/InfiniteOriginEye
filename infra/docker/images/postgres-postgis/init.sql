-- =============================================================================
-- SC&C Database Initialization
-- PostgreSQL 16 + PostGIS 3.4 + TimescaleDB
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "postgis_topology";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- =============================================================================
-- INCIDENT TABLE (S1 creates, S2 reviews, S3/S4 consume)
-- =============================================================================
CREATE TABLE incidents (
    incident_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at        TIMESTAMPTZ,

    -- Intake
    channel          TEXT NOT NULL CHECK (channel IN (
        'erss_112', 'citizen_app', 'sms', 'web_form', 'api_partner',
        'social_media', 'iot_sensor', 'early_warning', 'officer_report'
    )),
    status           TEXT NOT NULL DEFAULT 'created' CHECK (status IN (
        'created', 'ai_triaged', 'pending_review', 'approved', 'rejected',
        'dispatching', 'active', 'monitoring', 'closing', 'closed', 'archived'
    )),

    -- Reporter
    reporter_name    TEXT,
    reporter_phone   TEXT,
    contact_consent  BOOLEAN NOT NULL DEFAULT FALSE,

    -- Location (PostGIS geometry)
    location         GEOGRAPHY(POINT, 4326) NOT NULL,
    accuracy_m       FLOAT,
    reverse_geocode  TEXT,
    landmark         TEXT,
    state            TEXT,
    district         TEXT,

    -- Classification
    hazard_type      TEXT NOT NULL,
    severity         TEXT NOT NULL DEFAULT 'medium',
    estimated_scale  TEXT,

    -- Swarm decision
    needs_swarm          BOOLEAN NOT NULL DEFAULT FALSE,
    swarm_config         JSONB,
    needs_human_team     BOOLEAN NOT NULL DEFAULT FALSE,
    human_team_requests  TEXT[] DEFAULT '{}',

    -- Media & Description
    media_urls       TEXT[] DEFAULT '{}',
    summary_text     TEXT,

    -- AI Triage
    ai_confidence_score     FLOAT CHECK (ai_confidence_score BETWEEN 0 AND 1),
    ai_severity_prediction  TEXT,
    ai_swarm_recommendation JSONB,
    ai_embedding            vector(1536),  -- pgvector for similarity search

    -- Human Review
    professional_reviewer_id TEXT,
    review_timestamp         TIMESTAMPTZ,
    review_decision          TEXT,
    override_notes           TEXT,

    -- External IDs
    erss_incident_id   TEXT,
    ndmis_incident_id  TEXT,
    complaint_id       TEXT
);

-- Spatial index for location queries
CREATE INDEX idx_incidents_location ON incidents USING GIST (location);
CREATE INDEX idx_incidents_state ON incidents (state);
CREATE INDEX idx_incidents_status ON incidents (status);
CREATE INDEX idx_incidents_hazard ON incidents (hazard_type);
CREATE INDEX idx_incidents_created ON incidents (created_at DESC);
CREATE INDEX idx_incidents_erss ON incidents (erss_incident_id) WHERE erss_incident_id IS NOT NULL;

-- =============================================================================
-- MISSION TABLE (S3 creates/manages)
-- =============================================================================
CREATE TABLE missions (
    mission_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id   UUID NOT NULL REFERENCES incidents(incident_id),
    status        TEXT NOT NULL DEFAULT 'planned',
    area          GEOGRAPHY(POLYGON, 4326),
    swarm_config  JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX idx_missions_incident ON missions (incident_id);
CREATE INDEX idx_missions_status ON missions (status);

-- =============================================================================
-- DRONE REGISTRY
-- =============================================================================
CREATE TABLE drones (
    drone_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drone_type     TEXT NOT NULL CHECK (drone_type IN ('mother', 'ant', 'bee', 'medical')),
    serial_number  TEXT NOT NULL UNIQUE,
    status         TEXT NOT NULL DEFAULT 'idle',
    battery_pct    FLOAT NOT NULL DEFAULT 100 CHECK (battery_pct BETWEEN 0 AND 100),
    location       GEOGRAPHY(POINT, 4326),
    altitude_m     FLOAT,
    speed_ms       FLOAT,
    heading_deg    FLOAT,
    health         JSONB NOT NULL DEFAULT '{"gps":true,"imu":true,"motors":true,"camera":true,"comms":true}',
    mission_id     UUID REFERENCES missions(mission_id),
    legion_id      UUID,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_drones_mission ON drones (mission_id) WHERE mission_id IS NOT NULL;
CREATE INDEX idx_drones_type_status ON drones (drone_type, status);
CREATE INDEX idx_drones_location ON drones USING GIST (location);

-- =============================================================================
-- TELEMETRY TIME-SERIES (TimescaleDB hypertable)
-- =============================================================================
CREATE TABLE drone_telemetry (
    time          TIMESTAMPTZ NOT NULL,
    drone_id      UUID NOT NULL,
    latitude      FLOAT NOT NULL,
    longitude     FLOAT NOT NULL,
    altitude_m    FLOAT NOT NULL,
    speed_ms      FLOAT,
    heading_deg   FLOAT,
    battery_pct   FLOAT,
    health        JSONB
);

SELECT create_hypertable('drone_telemetry', 'time');
CREATE INDEX idx_telemetry_drone ON drone_telemetry (drone_id, time DESC);

-- =============================================================================
-- EARLY WARNING ALERTS (S5)
-- =============================================================================
CREATE TABLE early_warnings (
    alert_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source        TEXT NOT NULL CHECK (source IN ('imd', 'incois', 'cwc', 'gfs')),
    alert_type    TEXT NOT NULL,
    severity      TEXT NOT NULL,
    region        TEXT NOT NULL,
    location      GEOGRAPHY(POINT, 4326) NOT NULL,
    valid_from    TIMESTAMPTZ NOT NULL,
    valid_until   TIMESTAMPTZ NOT NULL,
    raw_payload   JSONB NOT NULL,
    incident_id   UUID REFERENCES incidents(incident_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_warnings_source ON early_warnings (source, created_at DESC);
CREATE INDEX idx_warnings_location ON early_warnings USING GIST (location);

-- =============================================================================
-- AUDIT TRAIL (S7 compliance)
-- =============================================================================
CREATE TABLE audit_log (
    audit_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id      TEXT NOT NULL,
    actor_role    TEXT NOT NULL,
    action        TEXT NOT NULL,
    entity_type   TEXT NOT NULL,
    entity_id     UUID NOT NULL,
    old_value     JSONB,
    new_value     JSONB,
    metadata      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_actor ON audit_log (actor_id, created_at DESC);

-- =============================================================================
-- RESCUE TEAMS (S4)
-- =============================================================================
CREATE TABLE rescue_teams (
    team_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_name     TEXT NOT NULL,
    agency        TEXT NOT NULL CHECK (agency IN ('NDRF', 'SDRF', 'Fire', 'Police', 'Health', 'Civil Defence', 'NGO')),
    team_type     TEXT NOT NULL,
    state         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'available',
    location      GEOGRAPHY(POINT, 4326),
    capabilities  TEXT[] DEFAULT '{}',
    personnel_count INT,
    mission_id    UUID REFERENCES missions(mission_id),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- STATES & DISTRICTS (Reference data)
-- =============================================================================
CREATE TABLE states_ref (
    state_code    TEXT PRIMARY KEY,
    state_name    TEXT NOT NULL,
    sdma_hq       TEXT NOT NULL,
    seoc_hq       TEXT NOT NULL,
    pilot_state   BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE districts_ref (
    district_code TEXT PRIMARY KEY,
    district_name TEXT NOT NULL,
    state_code    TEXT NOT NULL REFERENCES states_ref(state_code),
    location      GEOGRAPHY(POINT, 4326)
);

-- Pilot states seed
INSERT INTO states_ref (state_code, state_name, sdma_hq, seoc_hq, pilot_state) VALUES
    ('UK', 'Uttarakhand', 'Dehradun', 'Dehradun', TRUE),
    ('KL', 'Kerala', 'Thiruvananthapuram', 'Thiruvananthapuram', TRUE),
    ('TN', 'Tamil Nadu', 'Chennai', 'Chennai', TRUE),
    ('AS', 'Assam', 'Dispur', 'Guwahati', TRUE),
    ('HP', 'Himachal Pradesh', 'Shimla', 'Shimla', TRUE)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- COMPLETED
-- =============================================================================
