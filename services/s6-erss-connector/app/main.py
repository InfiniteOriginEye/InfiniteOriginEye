# =============================================================================
# S6 - ERSS/112 Connector
# Owner: ERSS/PSAP (operates) / C-DAC (builds)
# Tech: Python 3.11 + FastAPI + Kafka
# Port: 8006
#
# Phase 1: Outbound — Send SMS/email/phone alerts to 112 operators
# Phase 2: Inbound — Official API partnership with state ERSS PSAP systems
#   - Receive incidents from PSAP CAD systems
#   - Push swarm dispatch status back to PSAP
#   - Bi-directional sync via Kafka erss.incident_sync
# =============================================================================

import httpx
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("s6.erss_connector")

app = FastAPI(
    title="S6 - ERSS/112 Connector",
    description="Integration with state ERSS/112 PSAP systems, CAD dispatch, bi-directional sync",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# =============================================================================
# State PSAP Configurations
# =============================================================================

STATE_PSAP_CONFIGS = {
    "Uttarakhand": {
        "psap_vendor": "genasys", "cad_api": "https://uk-erss.nic.in/api/v1",
        "sms_gateway": "https://uk-erss.nic.in/sms", "email_alert": "seoc-uk@nic.in",
        "vpn_required": True, "mou_status": "phase1",
    },
    "Kerala": {
        "psap_vendor": "zetron", "cad_api": "https://kl-erss.nic.in/api/v1",
        "sms_gateway": "https://kl-erss.nic.in/sms", "email_alert": "seoc-kl@nic.in",
        "vpn_required": True, "mou_status": "phase1",
    },
    "Tamil Nadu": {
        "psap_vendor": "genasys", "cad_api": "https://tn-erss.nic.in/api/v1",
        "sms_gateway": "https://tn-erss.nic.in/sms", "email_alert": "seoc-tn@nic.in",
        "vpn_required": True, "mou_status": "pending",
    },
    "Assam": {
        "psap_vendor": "custom", "cad_api": "https://as-erss.nic.in/api/v1",
        "sms_gateway": "https://as-erss.nic.in/sms", "email_alert": "seoc-as@nic.in",
        "vpn_required": True, "mou_status": "pending",
    },
    "Himachal Pradesh": {
        "psap_vendor": "genasys", "cad_api": "https://hp-erss.nic.in/api/v1",
        "sms_gateway": "https://hp-erss.nic.in/sms", "email_alert": "seoc-hp@nic.in",
        "vpn_required": True, "mou_status": "phase1",
    },
}


class ERSSConnectorService:
    """Handles outbound alerts to ERSS/112 and inbound incident sync."""

    # MSG91 / BSNL SMS gateway for outbound alerts
    SMS_GATEWAY_URL = "https://api.msg91.com/api/v5/flow"
    SMS_AUTH_KEY = None  # Set from environment

    async def send_outbound_alert(
        self, state: str, incident_id: str, message: str,
        severity: str = "high", phone_numbers: list[str] = None,
    ) -> dict:
        """
        Phase 1: Send SMS + email alert to ERSS/112 operators in the state.

        This is how we notify 112 operators about incidents from our system
        that they may not have received through their own channels.
        """
        config = STATE_PSAP_CONFIGS.get(state)
        if not config:
            return {"success": False, "error": f"No ERSS config for state: {state}"}

        results = {"state": state, "sms": None, "email": None}

        # SMS alert to ERSS operators
        if phone_numbers and self.SMS_AUTH_KEY:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        self.SMS_GATEWAY_URL,
                        json={
                            "authkey": self.SMS_AUTH_KEY,
                            "mobiles": phone_numbers,
                            "message": f"[SC&C ALERT] Incident {incident_id}: {message} — Severity: {severity}",
                            "sender": "SCCALT",
                        },
                    )
                    results["sms"] = {"status": resp.status_code, "sent": len(phone_numbers)}
            except Exception as e:
                results["sms"] = {"error": str(e)}

        # Email alert to SEOC
        if config.get("email_alert"):
            results["email"] = {"to": config["email_alert"], "subject": f"[SC&C] {severity.upper()} - {incident_id}"}

        return results

    async def sync_incident_to_erss(
        self, state: str, incident_id: str, status: str, swarm_status: str = None,
    ) -> dict:
        """
        Phase 2: Push incident/swarm status back to ERSS PSAP.

        This keeps the 112 CAD system updated with our swarm deployment status
        so PSAP operators can see it on their dispatch consoles.
        """
        config = STATE_PSAP_CONFIGS.get(state, {})
        if config.get("mou_status") != "phase2":
            return {"success": False, "reason": f"State {state} MoU status: {config.get('mou_status', 'none')} — Phase 2 API not yet available"}

        # Phase 2: Call state PSAP CAD API
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.patch(
                    f"{config['cad_api']}/incidents/{incident_id}",
                    json={"status": status, "swarm_status": swarm_status},
                )
                return {"success": resp.status_code == 200, "erss_response": resp.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def receive_erss_incident(self, state: str, erss_data: dict) -> dict:
        """
        Phase 2: Receive incident from ERSS PSAP CAD system.

        ERSS operator creates incident → CAD dispatches →
        Also pushes to us via API → We create incident in S1 →
        Link with erss_incident_id for bi-directional sync.
        """
        # Translate ERSS schema → SC&C incident schema
        incident_data = {
            "channel": "erss_112",
            "erss_incident_id": erss_data.get("incident_id"),
            "reporter_phone": erss_data.get("caller_ani"),
            "latitude": erss_data.get("ali_latitude"),
            "longitude": erss_data.get("ali_longitude"),
            "reverse_geocode": erss_data.get("ali_address"),
            "state": state,
            "hazard_type": self._map_erss_type(erss_data.get("incident_type")),
            "severity": self._map_erss_priority(erss_data.get("priority")),
            "summary_text": erss_data.get("operator_notes", ""),
        }

        # Push to S1 via internal API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://s1-incident-intake:8001/api/v1/incidents",
                    json=incident_data,
                )
                return {"success": resp.status_code == 200, "s1_incident": resp.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _map_erss_type(code: str) -> str:
        mapping = {"FIRE": "fire", "FLOOD": "flood", "EQ": "earthquake",
                   "LS": "landslide", "CYC": "cyclone", "MED": "epidemic",
                   "ACC": "road_accident_mass", "BLD": "building_collapse"}
        return mapping.get((code or "").upper(), "other")

    @staticmethod
    def _map_erss_priority(p: str) -> str:
        mapping = {"P1": "critical", "P2": "high", "P3": "medium", "P4": "low"}
        return mapping.get((p or "").upper(), "medium")


erss_service = ERSSConnectorService()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s6-erss-connector"}

@app.get("/api/v1/erss/states")
async def list_state_configs():
    """List ERSS integration status for all pilot states."""
    return {
        "states": {
            state: {"vendor": c["psap_vendor"], "mou_status": c["mou_status"], "vpn_required": c["vpn_required"]}
            for state, c in STATE_PSAP_CONFIGS.items()
        }
    }

@app.post("/api/v1/erss/alert")
async def send_erss_alert(alert_data: dict):
    """Send outbound alert to ERSS/112 operators (Phase 1: SMS + email)."""
    return await erss_service.send_outbound_alert(
        state=alert_data.get("state", ""),
        incident_id=alert_data.get("incident_id", ""),
        message=alert_data.get("message", ""),
        severity=alert_data.get("severity", "high"),
        phone_numbers=alert_data.get("phone_numbers"),
    )

@app.post("/api/v1/erss/sync")
async def sync_to_erss(sync_data: dict):
    """Push incident status to ERSS CAD (Phase 2)."""
    return await erss_service.sync_incident_to_erss(
        state=sync_data.get("state", ""),
        incident_id=sync_data.get("incident_id", ""),
        status=sync_data.get("status", ""),
        swarm_status=sync_data.get("swarm_status"),
    )

@app.post("/api/v1/erss/inbound")
async def receive_from_erss(erss_data: dict):
    """Receive incident from ERSS PSAP (Phase 2 inbound)."""
    state = erss_data.get("state", "")
    return await erss_service.receive_erss_incident(state, erss_data)
