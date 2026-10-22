"""
Sachet Adapter - NDMA's Cap-Based Alert Platform
=================================================

Sachet (https://sachet.ndma.gov.in) is NDMA's Common Alerting Protocol (CAP)
platform. It aggregates alerts from:
  - IMD (weather, cyclone, earthquake)
  - CWC (flood)
  - INCOIS (tsunami)
  - State SDMAs

CAP 1.2 format — the international standard for emergency alerts.
This is our MOST IMPORTANT alert source because it normalizes all agencies.
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class SachetAdapter(BaseChannelAdapter):
    """NDMA Sachet CAP alert platform — unified multi-agency alerts."""

    channel_id = ChannelID.SACHET

    SACHET_API = "https://sachet.ndma.gov.in/api"

    # CAP severity → our severity
    CAP_SEVERITY_MAP = {
        "Extreme": "critical",
        "Severe": "high",
        "Moderate": "medium",
        "Minor": "low",
        "Unknown": "medium",
    }

    # CAP event types → our hazard types
    CAP_EVENT_MAP = {
        "Flood": "flood",
        "FlashFlood": "flood",
        "Cyclone": "cyclone",
        "TropicalCyclone": "cyclone",
        "Earthquake": "earthquake",
        "Tsunami": "tsunami",
        "Landslide": "landslide",
        "HeavyRain": "flood",
        "ThunderStorm": "other",
        "HeatWave": "other",
        "ColdWave": "other",
        "DustStorm": "other",
        "Cloudburst": "cloudburst",
        "Avalanche": "avalanche",
        "Fire": "fire",
        "Volcano": "other",
    }

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch CAP alerts from Sachet."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {"status": "Active"}
                if since:
                    params["sent_after"] = since.isoformat()
                resp = await client.get(f"{self.SACHET_API}/alerts", params=params)
                if resp.status_code == 200:
                    for alert in resp.json().get("alerts", []):
                        # Each CAP alert can have multiple info blocks (languages)
                        info = alert.get("info", [{}])[0] if alert.get("info") else {}
                        # Extract geo from CAP area blocks
                        area = info.get("area", [{}])[0] if info.get("area") else {}
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=alert,
                            source_id=alert.get("identifier"),
                            latitude=area.get("centroid", {}).get("lat"),
                            longitude=area.get("centroid", {}).get("lon"),
                            location_text=area.get("areaDesc"),
                            description=info.get("description"),
                            timestamp=datetime.fromisoformat(alert["sent"]) if "sent" in alert else None,
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
        info = data.get("info", [{}])[0] if data.get("info") else {}
        cap_severity = info.get("severity", "Unknown")
        cap_event = info.get("event", "")
        return {
            "channel": "early_warning",
            "hazard_type": self.CAP_EVENT_MAP.get(cap_event, "other"),
            "severity": self.CAP_SEVERITY_MAP.get(cap_severity, "medium"),
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "needs_swarm": self.CAP_SEVERITY_MAP.get(cap_severity) in ("critical", "high"),
        }
