# =============================================================================
# S1 - Incident Intake & Triage
# Owner: SDMA / SEOC
# Tech: Python 3.11 + FastAPI + Kafka + PostgreSQL/PostGIS
# Port: 8001
# =============================================================================

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .services.channels import ChannelID, HELPLINE_DIRECTORY, ADAPTERS
from .services.orchestrator import ChannelOrchestrator

# =============================================================================
# App Lifecycle — Start/Stop Orchestrator
# =============================================================================

orchestrator = ChannelOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start channel orchestrator on startup, stop on shutdown."""
    await orchestrator.start()
    yield
    await orchestrator.stop()


app = FastAPI(
    title="S1 - Incident Intake & Triage",
    description="Multi-channel incident ingestion from all Indian disaster helplines, "
                "AI triage scoring, human-in-the-loop review queue",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s1-incident-intake"}


@app.get("/api/v1/channels/status")
async def channels_status():
    """Get status of all helpline channel adapters."""
    return orchestrator.get_status()


@app.get("/api/v1/channels/directory")
async def helpline_directory():
    """Complete directory of all Indian disaster helplines with contact info."""
    return {
        "total": len(HELPLINE_DIRECTORY),
        "helplines": {
            cid.value: {
                "name": info.name,
                "number": info.number,
                "operator": info.operator,
                "scope": info.scope,
                "coverage": info.coverage,
                "available_24x7": info.available_24x7,
                "api_available": info.api_available,
                "api_type": info.api_type,
                "fetch_strategy": info.fetch_strategy,
                "priority": info.priority,
                "notes": info.notes,
            }
            for cid, info in HELPLINE_DIRECTORY.items()
        },
    }


# =============================================================================
# INCIDENT ENDPOINTS
# =============================================================================

@app.get("/api/v1/incidents")
async def list_incidents(
    channel: Optional[str] = None,
    state: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List incidents with filters. (DB-backed — placeholder for now)"""
    return {"incidents": [], "total": 0, "limit": limit, "offset": offset}


@app.post("/api/v1/incidents")
async def create_incident(incident_data: dict, background_tasks: BackgroundTasks):
    """
    Create a new incident from any channel.
    This is the primary intake endpoint for webhook-based channels.
    """
    channel_str = incident_data.get("channel", "citizen_app")
    try:
        channel_id = ChannelID(channel_str)
    except ValueError:
        channel_id = ChannelID.CITIZEN_APP

    # Process through orchestrator
    result = await orchestrator.process_webhook(channel_id, incident_data)
    return {
        "status": "created",
        "channel": channel_str,
        "processing_result": result,
    }


# =============================================================================
# WEBHOOK ENDPOINTS (called by external services)
# =============================================================================

@app.post("/api/v1/webhook/whatsapp")
async def whatsapp_webhook(payload: dict, background_tasks: BackgroundTasks):
    """WhatsApp Business API webhook — citizen disaster reports via WhatsApp."""
    result = await orchestrator.process_webhook(ChannelID.WHATSAPP_BUSINESS, payload)
    return {"status": "received", "result": result}


@app.post("/api/v1/webhook/sms")
async def sms_webhook(payload: dict, background_tasks: BackgroundTasks):
    """SMS gateway webhook — inbound SMS from shortcode."""
    result = await orchestrator.process_webhook(ChannelID.SMS_SHORTCODE, payload)
    return {"status": "received", "result": result}


@app.post("/api/v1/webhook/citizen-app")
async def citizen_app_webhook(payload: dict, background_tasks: BackgroundTasks):
    """S10 Citizen App webhook — structured incident reports from mobile app."""
    result = await orchestrator.process_webhook(ChannelID.CITIZEN_APP, payload)
    return {"status": "received", "result": result}


@app.post("/api/v1/webhook/ndrf-whatsapp")
async def ndrf_whatsapp_webhook(payload: dict, background_tasks: BackgroundTasks):
    """NDRF WhatsApp (917566363636) webhook."""
    result = await orchestrator.process_webhook(ChannelID.NDRF_WHATSAPP, payload)
    return {"status": "received", "result": result}


@app.post("/api/v1/webhook/social-media")
async def social_media_webhook(payload: dict, background_tasks: BackgroundTasks):
    """Social media monitoring webhook (Twitter, Facebook)."""
    result = await orchestrator.process_webhook(ChannelID.SOCIAL_MEDIA, payload)
    return {"status": "received", "result": result}


# =============================================================================
# IoT SENSOR ENDPOINTS (MQTT bridge posts here)
# =============================================================================

@app.post("/api/v1/iot/flood/{sensor_id}")
async def iot_flood_sensor(sensor_id: str, payload: dict):
    """IoT flood sensor data — water level alerts."""
    result = await orchestrator.process_mqtt_message(ChannelID.IOT_FLOOD_SENSOR, sensor_id, payload)
    return {"sensor_id": sensor_id, "result": result}


@app.post("/api/v1/iot/seismic/{sensor_id}")
async def iot_seismic_sensor(sensor_id: str, payload: dict):
    """IoT seismic sensor data — earthquake detection."""
    result = await orchestrator.process_mqtt_message(ChannelID.IOT_SEISMIC, sensor_id, payload)
    return {"sensor_id": sensor_id, "result": result}


@app.post("/api/v1/iot/rain/{sensor_id}")
async def iot_rain_sensor(sensor_id: str, payload: dict):
    """IoT rain gauge data — heavy rainfall alerts."""
    result = await orchestrator.process_mqtt_message(ChannelID.IOT_RAIN_GAUGE, sensor_id, payload)
    return {"sensor_id": sensor_id, "result": result}


# =============================================================================
# MANUAL ENTRY (for channels without APIs — Armed Forces, CAPF, NDRF)
# =============================================================================

@app.post("/api/v1/incidents/manual")
async def manual_incident(incident_data: dict):
    """
    Manual incident entry by SEOC Duty Officer or field personnel.
    Used for channels without programmatic access:
      - NDRF Control Room (011-26144044)
      - Indian Army/AF/Navy/Coast Guard HADR
      - BSF/CISF/CRPF/SSB
      - Red Cross / NGOs
    """
    channel_str = incident_data.get("channel", "officer_report")
    try:
        channel_id = ChannelID(channel_str)
    except ValueError:
        channel_id = ChannelID.CITIZEN_APP

    incident_data["status"] = "pending_review"  # Manual entries skip AI triage
    result = await orchestrator.process_webhook(channel_id, incident_data)
    return {"status": "created", "channel": channel_str, "result": result}
