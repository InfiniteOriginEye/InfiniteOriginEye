"""
IMD Adapter - India Meteorological Department
=============================================

IMD provides REST APIs for:
  - Weather warnings (rain, thunderstorm, heat wave, cold wave)
  - Cyclone alerts (Bay of Bengal & Arabian Sea)
  - Earthquake information (seismo.gov.in)
  - Heavy rainfall alerts
  - Fog alerts

API endpoints:
  - https://mausam.imd.gov.in/api/weather_data
  - https://mausam.imd.gov.in/api/cyclone
  - https://seismo.gov.in/api/earthquake
  - RSS feeds for warnings

CAP (Common Alerting Protocol) format for Sachet integration.
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class IMDAdapter(BaseChannelAdapter):
    """IMD weather, cyclone, and earthquake alert ingestion."""

    channel_id = ChannelID.IMD

    # IMD API endpoints
    WEATHER_WARNING_URL = "https://mausam.imd.gov.in/api/weather_warning"
    CYCLONE_URL = "https://mausam.imd.gov.in/api/cyclone"
    EARTHQUAKE_URL = "https://seismo.gov.in/api/earthquake"
    RAINFALL_URL = "https://mausam.imd.gov.in/api/rainfall"
    RSS_WARNING_URL = "https://mausam.imd.gov.in/rss/weather_warning.xml"

    # IMD warning severity mapping
    IMD_SEVERITY_MAP = {
        "RED": "critical",
        "ORANGE": "high",
        "YELLOW": "medium",
        "GREEN": "low",
    }

    # IMD hazard type mapping
    IMD_HAZARD_MAP = {
        "HEAVY RAIN": "flood",
        "VERY HEAVY RAIN": "flood",
        "EXTREMELY HEAVY RAIN": "flood",
        "THUNDERSTORM": "other",
        "CYCLONE": "cyclone",
        "HEAT WAVE": "other",
        "COLD WAVE": "other",
        "FOG": "other",
        "LANDSLIDE": "landslide",
        "CLOUDBURST": "cloudburst",
        "FLOOD": "flood",
        "EARTHQUAKE": "earthquake",
        "TSUNAMI": "tsunami",
    }

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch all IMD alerts: weather warnings + cyclone + earthquake."""
        all_incidents = []
        errors = []

        # Weather warnings
        try:
            weather = await self._fetch_weather_warnings(since)
            all_incidents.extend(weather)
        except Exception as e:
            errors.append(f"weather: {e}")

        # Cyclone alerts
        try:
            cyclone = await self._fetch_cyclone_alerts(since)
            all_incidents.extend(cyclone)
        except Exception as e:
            errors.append(f"cyclone: {e}")

        # Earthquake info
        try:
            quake = await self._fetch_earthquake_info(since)
            all_incidents.extend(quake)
        except Exception as e:
            errors.append(f"earthquake: {e}")

        # Heavy rainfall
        try:
            rainfall = await self._fetch_rainfall_alerts(since)
            all_incidents.extend(rainfall)
        except Exception as e:
            errors.append(f"rainfall: {e}")

        return FetchResult(
            channel_id=self.channel_id,
            success=len(errors) == 0,
            incidents=all_incidents,
            error="; ".join(errors) if errors else None,
            fetched_at=datetime.now(timezone.utc),
        )

    async def _fetch_weather_warnings(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch IMD weather warnings (CAP format via Sachet)."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try Sachet CAP feed first (more structured)
            try:
                resp = await client.get(
                    "https://sachet.ndma.gov.in/api/alerts",
                    params={"source": "IMD", "since": since.isoformat() if since else None},
                )
                if resp.status_code == 200:
                    for alert in resp.json().get("alerts", []):
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=alert,
                            source_id=alert.get("alert_id"),
                            latitude=alert.get("latitude"),
                            longitude=alert.get("longitude"),
                            location_text=alert.get("area_desc"),
                            description=alert.get("description"),
                            timestamp=datetime.fromisoformat(alert["sent"]) if "sent" in alert else None,
                        ))
                    return incidents
            except Exception:
                pass

            # Fallback: direct IMD API
            resp = await client.get(self.WEATHER_WARNING_URL)
            if resp.status_code == 200:
                data = resp.json()
                for warning in data.get("warnings", []):
                    incidents.append(RawIncident(
                        channel_id=self.channel_id,
                        raw_data=warning,
                        source_id=warning.get("id"),
                        latitude=warning.get("lat"),
                        longitude=warning.get("lon"),
                        location_text=warning.get("region"),
                        description=warning.get("warning_text"),
                    ))
        return incidents

    async def _fetch_cyclone_alerts(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch cyclone warnings from IMD."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.CYCLONE_URL)
                if resp.status_code == 200:
                    for cyclone in resp.json().get("cyclones", []):
                        incidents.append(RawIncident(
                            channel_id=ChannelID.CYCLONE_IMD,
                            raw_data=cyclone,
                            source_id=cyclone.get("cyclone_id"),
                            latitude=cyclone.get("center_lat"),
                            longitude=cyclone.get("center_lon"),
                            location_text=cyclone.get("name", "Unnamed Cyclone"),
                            description=f"Cyclone {cyclone.get('name')}: {cyclone.get('category')} — Wind: {cyclone.get('max_wind_kph')} kph",
                        ))
            except Exception:
                pass
        return incidents

    async def _fetch_earthquake_info(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch earthquake information from IMD/NCS."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.EARTHQUAKE_URL, params={"limit": 20})
                if resp.status_code == 200:
                    for eq in resp.json().get("earthquakes", []):
                        incidents.append(RawIncident(
                            channel_id=ChannelID.EARTHQUAKE_IMD,
                            raw_data=eq,
                            source_id=eq.get("eq_id"),
                            latitude=float(eq.get("latitude", 0)),
                            longitude=float(eq.get("longitude", 0)),
                            description=f"M{eq.get('magnitude')} earthquake at {eq.get('depth_km')}km depth — {eq.get('location')}",
                        ))
            except Exception:
                pass
        return incidents

    async def _fetch_rainfall_alerts(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch heavy rainfall warnings from IMD."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.RAINFALL_URL, params={"type": "warning"})
                if resp.status_code == 200:
                    for alert in resp.json().get("alerts", []):
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=alert,
                            source_id=alert.get("id"),
                            latitude=alert.get("lat"),
                            longitude=alert.get("lon"),
                            location_text=alert.get("subdivision"),
                            description=f"Rainfall alert: {alert.get('category')} — {alert.get('amount_mm')}mm expected",
                        ))
            except Exception:
                pass
        return incidents

    async def normalize(self, raw: RawIncident) -> dict:
        """Normalize IMD alert to canonical incident format."""
        data = raw.raw_data
        severity_raw = data.get("severity") or data.get("color_code") or "YELLOW"

        return {
            "channel": "early_warning",
            "hazard_type": self.IMD_HAZARD_MAP.get(
                (data.get("event") or data.get("warning_type") or "").upper(), "other"
            ),
            "severity": self.IMD_SEVERITY_MAP.get(severity_raw.upper(), "medium"),
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "needs_swarm": self.IMD_SEVERITY_MAP.get(severity_raw.upper(), "medium") in ("critical", "high"),
        }

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://mausam.imd.gov.in/api/health")
                return resp.status_code == 200
        except Exception:
            return False
