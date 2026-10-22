"""
ERSS/112 Adapter - Emergency Response Support System
====================================================

India's 112 helpline is state-centric. Each state runs its own PSAP (Public Safety
Answering Point) with CAD (Computer-Aided Dispatch) and GIS.

Phase 1: Outbound only — we send SMS/email alerts to 112 operators
Phase 2: Inbound — official MoU for API access to PSAP CAD systems

No public API exists. Integration requires:
  - State-level MoU between SDMA and ERSS operator
  - VPN tunnel to PSAP network
  - CAD system API credentials (different per state: Genasys, Zetron, etc.)
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import (
    BaseChannelAdapter, ChannelID, FetchResult, RawIncident,
    HELPLINE_DIRECTORY,
)


class ERSS112Adapter(BaseChannelAdapter):
    """
    Adapter for ERSS/112 state PSAP systems.

    Since there's no public API, we use:
      - Phase 1: Simulated inbound via seed data + cron
      - Phase 2: State-specific CAD connectors (Genasys, Zetron, etc.)
      - Always: Outbound SMS/email to 112 operators via our S6 connector
    """

    channel_id = ChannelID.ERSS_112

    # State-specific PSAP endpoints (Phase 2 — after MoU)
    STATE_PSAP_CONFIGS = {
        "Uttarakhand": {
            "psap_vendor": "genasys",
            "cad_api_base": "https://uk-erss.nic.in/api/v1",
            "vpn_required": True,
        },
        "Kerala": {
            "psap_vendor": "zetron",
            "cad_api_base": "https://kl-erss.nic.in/api/v1",
            "vpn_required": True,
        },
        "Tamil Nadu": {
            "psap_vendor": "genasys",
            "cad_api_base": "https://tn-erss.nic.in/api/v1",
            "vpn_required": True,
        },
        "Assam": {
            "psap_vendor": "custom",
            "cad_api_base": "https://as-erss.nic.in/api/v1",
            "vpn_required": True,
        },
        "Himachal Pradesh": {
            "psap_vendor": "genasys",
            "cad_api_base": "https://hp-erss.nic.in/api/v1",
            "vpn_required": True,
        },
    }

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """
        Fetch incidents from ERSS/112.

        Phase 1: Returns empty — we rely on S6 connector for ERSS sync.
        Phase 2: Poll state PSAP CAD APIs for new incidents.
        """
        # Phase 2 implementation:
        incidents = []
        for state, config in self.STATE_PSAP_CONFIGS.items():
            try:
                state_incidents = await self._fetch_state_psap(state, config, since)
                incidents.extend(state_incidents)
            except Exception as e:
                # Log but don't fail — other states may still work
                continue

        return FetchResult(
            channel_id=self.channel_id,
            success=True,
            incidents=incidents,
            fetched_at=datetime.now(timezone.utc),
        )

    async def _fetch_state_psap(
        self, state: str, config: dict, since: Optional[datetime]
    ) -> list[RawIncident]:
        """Fetch from a specific state's PSAP CAD system."""
        # Phase 1: Not yet connected — return empty
        # Phase 2: Call CAD API
        return []

    async def normalize(self, raw: RawIncident) -> dict:
        """
        Normalize ERSS incident to canonical format.

        ERSS CAD systems typically provide:
          - Caller ANI (phone number)
          - ALI (Automatic Location Information)
          - Incident type code
          - Operator notes
          - Dispatch status
        """
        data = raw.raw_data
        return {
            "channel": "erss_112",
            "erss_incident_id": raw.source_id,
            "reporter_phone": data.get("caller_ani") or raw.caller_phone,
            "latitude": data.get("ali_latitude") or raw.latitude,
            "longitude": data.get("ali_longitude") or raw.longitude,
            "reverse_geocode": data.get("ali_address"),
            "hazard_type": self._map_incident_type(data.get("incident_type_code")),
            "summary_text": data.get("operator_notes") or raw.description,
            "state": data.get("state"),
        }

    async def send_alert(self, incident_id: str, message: str) -> bool:
        """
        Send outbound alert to ERSS/112 operators.

        This calls S6 (ERSS Connector) which handles the actual
        SMS/email/phone call dispatch to 112 operators.
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    "http://s6-erss-connector:8006/api/v1/erss/alert",
                    json={"incident_id": incident_id, "message": message},
                    timeout=10.0,
                )
                return resp.status_code == 200
            except Exception:
                return False

    @staticmethod
    def _map_incident_type(code: Optional[str]) -> str:
        """Map ERSS incident type codes to our hazard types."""
        if not code:
            return "other"
        mapping = {
            "FIRE": "fire",
            "FLOOD": "flood",
            "EQ": "earthquake",
            "LS": "landslide",
            "CYC": "cyclone",
            "MED": "epidemic",
            "ACC": "road_accident_mass",
            "BLD": "building_collapse",
            "IND": "industrial",
        }
        return mapping.get(code.upper(), "other")
