"""
RailMadad & Sector-Specific Adapters
=====================================

RailMadad (139): Railway emergency + grievance system.
Fire 101, Police 100, Ambulance 108: State helplines (via ERSS integration).
NDRF WhatsApp: WhatsApp Business for citizen reports.
CPGRAMS: Centralized public grievance system.
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class RailMadadAdapter(BaseChannelAdapter):
    """RailMadad (139) — Railway emergency & grievance ingestion."""

    channel_id = ChannelID.RAILMADAD

    RAILMADAD_API = "https://railmadad.indianrailways.gov.in/api"

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch railway emergency incidents from RailMadad API."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {"category": "emergency", "status": "open"}
                if since:
                    params["since"] = since.isoformat()
                resp = await client.get(f"{self.RAILMADAD_API}/complaints", params=params)
                if resp.status_code == 200:
                    for complaint in resp.json().get("complaints", []):
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=complaint,
                            source_id=complaint.get("complaint_id"),
                            caller_phone=complaint.get("mobile"),
                            latitude=complaint.get("latitude"),
                            longitude=complaint.get("longitude"),
                            location_text=complaint.get("station_name"),
                            description=f"Railway emergency: {complaint.get('complaint_type')} — "
                                       f"{complaint.get('description')} — "
                                       f"Train: {complaint.get('train_no', 'N/A')}",
                        ))
            except Exception as e:
                return FetchResult(
                    channel_id=self.channel_id, success=False,
                    error=str(e), fetched_at=datetime.now(timezone.utc),
                )

        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=incidents, fetched_at=datetime.now(timezone.utc),
        )

    async def normalize(self, raw: RawIncident) -> dict:
        data = raw.raw_data
        complaint_type = (data.get("complaint_type") or "").lower()
        hazard = "fire" if "fire" in complaint_type else \
                 "road_accident_mass" if "accident" in complaint_type else \
                 "building_collapse" if "bridge" in complaint_type or "collapse" in complaint_type else "other"
        return {
            "channel": "api_partner",
            "hazard_type": hazard,
            "severity": "high",
            "reporter_phone": raw.caller_phone,
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "complaint_id": raw.source_id,
        }


class StateHelplineAdapter(BaseChannelAdapter):
    """
    Generic adapter for state-level helplines (Fire 101, Police 100, Ambulance 108).
    
    These are integrated through ERSS/112 in most states.
    For states without ERSS, we poll their individual control rooms.
    """

    channel_id = ChannelID.FIRE_101  # Default; overridden per instance

    def __init__(self, channel_id: ChannelID, state: str = ""):
        self.channel_id = channel_id
        self.state = state
        super().__init__()

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """
        State helplines are typically consumed through ERSS/112.
        This adapter handles states where ERSS is not yet deployed.
        """
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def normalize(self, raw: RawIncident) -> dict:
        return {
            "channel": "erss_112",  # Routed through ERSS
            "hazard_type": "fire" if "fire" in self.channel_id.value else "other",
            "severity": "high",
            "summary_text": raw.description,
        }


class NDRFWhatsAppAdapter(BaseChannelAdapter):
    """NDRF WhatsApp (917566363636) for citizen disaster reports."""

    channel_id = ChannelID.NDRF_WHATSAPP

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """WhatsApp is webhook-based."""
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def normalize(self, raw: RawIncident) -> dict:
        return {
            "channel": "whatsapp_business",
            "reporter_phone": raw.caller_phone,
            "hazard_type": "other",
            "severity": "medium",
            "summary_text": raw.description,
            "media_urls": raw.media_urls,
            "needs_swarm": False,
        }


class CPGRAMSAdapter(BaseChannelAdapter):
    """CPGRAMS — Centralized Public Grievance Redress and Monitoring System."""

    channel_id = ChannelID.CPGRAMS

    CPGRAMS_API = "https://pgportal.gov.in/api"

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch disaster-related grievances from CPGRAMS."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {"ministry": "MHA", "status": "pending", "category": "disaster"}
                if since:
                    params["since"] = since.isoformat()
                resp = await client.get(f"{self.CPGRAMS_API}/grievances", params=params)
                if resp.status_code == 200:
                    for grievance in resp.json().get("grievances", []):
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=grievance,
                            source_id=grievance.get("grievance_id"),
                            caller_phone=grievance.get("mobile"),
                            description=f"CPGRAMS grievance: {grievance.get('subject')} — {grievance.get('description')}",
                        ))
            except Exception as e:
                return FetchResult(
                    channel_id=self.channel_id, success=False,
                    error=str(e), fetched_at=datetime.now(timezone.utc),
                )

        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=incidents, fetched_at=datetime.now(timezone.utc),
        )

    async def normalize(self, raw: RawIncident) -> dict:
        return {
            "channel": "api_partner",
            "hazard_type": "other",
            "severity": "low",
            "summary_text": raw.description,
            "complaint_id": raw.source_id,
        }
