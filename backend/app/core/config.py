"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and .env support.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────
    APP_NAME: str = "SwarmCommandControl"
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    # ── Database ─────────────────────────────────────
    POSTGRES_DSN: str = "postgresql+asyncpg://scc:scc@localhost:5432/scc"

    # ── Redis ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Kafka ────────────────────────────────────────
    KAFKA_BROKERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "scc-backend"

    # ── MQTT ─────────────────────────────────────────
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883

    # ── Triton ───────────────────────────────────────
    TRITON_URL: str = "http://localhost:8000"
    TRITON_GRPC_URL: str = "localhost:8001"

    # ── MinIO ────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "sccminio"
    MINIO_SECRET_KEY: str = "sccminio123"
    MINIO_BUCKET: str = "scc-media"

    # ── Auth ─────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── IMD API ──────────────────────────────────────
    IMD_API_BASE_URL: str = "https://api.imd.gov.in"
    IMD_API_KEY: str = ""

    # ── ERSS ─────────────────────────────────────────
    ERSS_API_BASE_URL: str = ""
    ERSS_API_KEY: str = ""

    # ── State defaults ───────────────────────────────
    DEFAULT_STATE: str = "UT"
    DEFAULT_DISTRICT: str = "DDN"

    # ── Simulation ───────────────────────────────────
    SIM_NUM_MOTHERS: int = 1
    SIM_DRONES_PER_LEGION: int = 25
    SIM_TELEMETRY_INTERVAL_MS: int = 200

    # ── SLAs ─────────────────────────────────────────
    SLA_AI_TRIAGE_MAX: int = 30
    SLA_HUMAN_REVIEW_MAX: int = 120
    SLA_SWARM_DISPATCH_MAX: int = 300
    SLA_AUTO_APPROVE_ON_TIMEOUT: bool = True

    # ── CORS ─────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",   # SEOC dashboard
        "http://localhost:3001",   # Swarm controller
        "http://localhost:3002",   # Grafana
    ]


settings = Settings()
