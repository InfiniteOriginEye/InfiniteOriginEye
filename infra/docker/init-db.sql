-- Init database extensions for SC&C
-- TimescaleDB, PostGIS, pgvector

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT postgis_full_version();
