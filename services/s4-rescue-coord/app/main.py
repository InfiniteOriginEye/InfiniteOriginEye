# =============================================================================
# S4 - Rescue Team Coordination
# Owner: NDRF / SDRF / Health-NHM
# Tech: Python 3.11 + FastAPI + Kafka
# Port: 8004
#
# Field team tracking, comms relay via Bee drones, patient handover,
# offline-first with ServiceWorker + IndexedDB on React Native.
# =============================================================================

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

logger = logging.getLogger("s4.rescue_coord")


class TeamStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    OPERATING = "operating"
    RETURNING = "returning"
    OFFLINE = "offline"


class PatientStatus(str, Enum):
    LOCATED = "located"
    RESCUED = "rescued"
    STABILIZED = "stabilized"
    IN_AMBULANCE = "in_ambulance"
    AT_HOSPITAL = "at_hospital"


# In-memory stores
teams_store: dict[str, dict] = {}
patient_store: dict[str, dict] = {}
handover_log: list[dict] = []


class RescueCoordService:
    """Manages rescue team dispatch, tracking, comms, and patient handover."""

    async def dispatch_team(self, team_id: str, mission_id: str, incident_id: str) -> dict:
        """Dispatch a rescue team to a mission/incident."""
        team = teams_store.get(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        if team["status"] != TeamStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail=f"Team {team_id} not available — status: {team['status']}")

        team["status"] = TeamStatus.DISPATCHED
        team["mission_id"] = mission_id
        team["incident_id"] = incident_id
        team["dispatched_at"] = datetime.now(timezone.utc).isoformat()

        # Notify S3 to coordinate Bee drone relay for this team
        logger.info(f"Team {team_id} dispatched to mission {mission_id}")

        return {"team_id": team_id, "status": "dispatched", "mission_id": mission_id}

    async def update_team_location(self, team_id: str, lat: float, lon: float, accuracy_m: float = None) -> dict:
        """Update team GPS position (from mobile app, 30-second intervals)."""
        team = teams_store.get(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

        team["last_location"] = {
            "latitude": lat, "longitude": lon, "accuracy_m": accuracy_m,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {"team_id": team_id, "updated": True}

    async def update_team_status(self, team_id: str, status: TeamStatus) -> dict:
        """Update team operational status."""
        team = teams_store.get(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

        team["status"] = status
        team["status_updated_at"] = datetime.now(timezone.utc).isoformat()
        return {"team_id": team_id, "status": status}

    async def create_patient(self, incident_id: str, location: dict, condition: str, priority: str = "urgent") -> dict:
        """Create a patient/victim record at the disaster scene."""
        patient_id = f"pat-{len(patient_store)+1}"
        patient = {
            "patient_id": patient_id,
            "incident_id": incident_id,
            "status": PatientStatus.LOCATED,
            "location": location,
            "condition": condition,
            "priority": priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "handover_chain": [],
        }
        patient_store[patient_id] = patient
        logger.info(f"Patient {patient_id} created — {condition} at {location}")
        return patient

    async def patient_handover(
        self, patient_id: str, from_entity: str, to_entity: str,
        to_type: str, notes: str = None,
    ) -> dict:
        """
        Record patient handover in the chain:
          Field Team → Ambulance → Hospital (NHM)
          or: Field Team → Medical Drone → Field Hospital
        """
        patient = patient_store.get(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        handover = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": from_entity,
            "to": to_entity,
            "to_type": to_type,  # "ambulance", "hospital", "drone_medical", "field_hospital"
            "notes": notes,
        }
        patient["handover_chain"].append(handover)
        handover_log.append(handover)

        # Update patient status based on destination
        if to_type == "ambulance":
            patient["status"] = PatientStatus.IN_AMBULANCE
        elif to_type in ("hospital", "field_hospital"):
            patient["status"] = PatientStatus.AT_HOSPITAL
        elif to_type == "drone_medical":
            patient["status"] = PatientStatus.STABILIZED

        return {"patient_id": patient_id, "status": patient["status"], "handover": handover}


rescue_service = RescueCoordService()

app = FastAPI(
    title="S4 - Rescue Team Coordination",
    description="Field team tracking, comms relay, patient handover, offline-first",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s4-rescue-coord", "teams": len(teams_store), "patients": len(patient_store)}


# --- Teams ---

@app.get("/api/v1/teams")
async def list_teams(agency: Optional[str] = None, status: Optional[str] = None):
    teams = list(teams_store.values())
    if agency:
        teams = [t for t in teams if t.get("agency") == agency]
    if status:
        teams = [t for t in teams if t.get("status") == status]
    return {"teams": teams, "count": len(teams)}

@app.post("/api/v1/teams")
async def register_team(team_data: dict):
    team_id = team_data.get("team_id") or f"team-{len(teams_store)+1}"
    team_data["team_id"] = team_id
    team_data["status"] = team_data.get("status", TeamStatus.AVAILABLE)
    teams_store[team_id] = team_data
    return {"team_id": team_id, "status": "registered"}

@app.post("/api/v1/teams/{team_id}/dispatch")
async def dispatch_team(team_id: str, dispatch_data: dict):
    return await rescue_service.dispatch_team(
        team_id, dispatch_data["mission_id"], dispatch_data["incident_id"]
    )

@app.post("/api/v1/teams/{team_id}/location")
async def update_team_location(team_id: str, location: dict):
    return await rescue_service.update_team_location(
        team_id, location["latitude"], location["longitude"], location.get("accuracy_m")
    )

@app.post("/api/v1/teams/{team_id}/status")
async def update_team_status(team_id: str, status_data: dict):
    return await rescue_service.update_team_status(team_id, TeamStatus(status_data["status"]))


# --- Patients ---

@app.post("/api/v1/patients")
async def create_patient(patient_data: dict):
    return await rescue_service.create_patient(
        patient_data["incident_id"], patient_data.get("location", {}),
        patient_data.get("condition", "unknown"), patient_data.get("priority", "urgent"),
    )

@app.get("/api/v1/patients/{patient_id}")
async def get_patient(patient_id: str):
    patient = patient_store.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.post("/api/v1/patients/{patient_id}/handover")
async def patient_handover(patient_id: str, handover_data: dict):
    return await rescue_service.patient_handover(
        patient_id, handover_data["from"], handover_data["to"],
        handover_data["to_type"], handover_data.get("notes"),
    )

@app.get("/api/v1/patients/{patient_id}/handover-chain")
async def get_handover_chain(patient_id: str):
    patient = patient_store.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient_id": patient_id, "chain": patient.get("handover_chain", [])}


# --- Comms relay via Bee drones ---

@app.post("/api/v1/comms/relay")
async def comms_relay(message: dict):
    """
    Relay message through Bee drone MQTT bridge.
    Used when cellular network is down — Bee drones act as comm relays.
    """
    # In production: Publish to MQTT scc/relay/{team_id}/message
    return {"status": "relayed", "via": "bee_drone_relay", "message_id": message.get("id")}
