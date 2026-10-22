# =============================================================================
# S5 - Early-Warning Ingest
# Owner: SDMA / SEOC
# Tech: Python 3.11 + FastAPI + Kafka
# Port: 8005
# =============================================================================

from fastapi import FastAPI

app = FastAPI(
    title="S5 - Early-Warning Ingest",
    description="IMD/INCOIS/CWC/GFS feed ingestion, threshold analysis, automated alerting",
    version="0.1.0",
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s5-early-warning"}

# Feeds:
#   IMD  - India Meteorological Department (cyclone, heavy rain, thunderstorm)
#   INCOIS - Indian National Centre for Ocean Information (tsunami, storm surge)
#   CWC  - Central Water Commission (flood, dam break)
#   GFS  - Global Forecast System (weather models)
# Each feed has its own ingest adapter under app/services/ingest/
# Threshold rules trigger Kafka "alerts.early_warning" → S1 auto-creates incidents
