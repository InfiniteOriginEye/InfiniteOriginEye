"""
INCOIS Adapter - Indian National Centre for Ocean Information Services
======================================================================

INCOIS provides:
  - Tsunami early warnings (TWS)
  - Ocean state forecasts (OSF)
  - Storm surge alerts
  - Potential fishing zone info
  - Tidal gauge data (real-time)

API: https://incois.gov.in/tms/API/
  - /tms/warnings - Active tsunami/storm surge warnings
  - /osf/forecast - Ocean state forecast
  - /tidal/realtime - Real-time tidal gauge readings
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class INCOISAdapter(BaseChannelAdapter):
    """INCOIS tsunami, storm surge, and ocean alert ingestion."""

    channel_id = ChannelID.INCOIS

    INCOIS_TMS_URL = "https://incois.gov.in/tms/api/warnings"
    INCOIS_TIDAL_URL = "https://incois.gov.in/tidal/api/realtime"
    INCOIS_OSF_URL = "https://incois.gov.in/osf/api/forecast"

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch INCOIS tsunami warnings + tidal anomalies + storm surge."""
        incidents = []
        errors = []

        try:
            tsunami = await self._fetch_tsunami_warnings(since)
            incidents.extend(tsunami)
        except Exception as e:
            errors.append(f"tsunami: {e}")

        try:
            tidal = await self._fetch_tidal_anomalies(since)
            incidents.extend(tidal)
        except Exception as e:
            errors.append(f"tidal: {e}")

        try:
            storm = await self._fetch_storm_surge(since)
            incidents.extend(storm)
        except Exception as e:
            errors.append(f"storm_surge: {e}")

        return FetchResult(
            channel_id=self.channel_id,
            success=len(errors) == 0,
            incidents=incidents,
            error="; ".join(errors) if errors else None,
            fetched_at=datetime.now(timezone.utc),
        )

    async def _fetch_tsunami_warnings(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch active tsunami warnings from INCOIS TMS."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.INCOIS_TMS_URL, params={"status": "active"})
                if resp.status_code == 200:
                    for warning in resp.json().get("warnings", []):
                        # Tsunami warnings cover coastal regions
                        for region in warning.get("affected_regions", []):
                            incidents.append(RawIncident(
                                channel_id=ChannelID.COASTAL_ALERT,
                                raw_data=warning,
                                source_id=warning.get("warning_id"),
                                latitude=region.get("lat"),
                                longitude=region.get("lon"),
                                location_text=region.get("coastal_state"),
                                description=f"Tsunami alert: {warning.get('level')} — ETA: {warning.get('eta')} — {warning.get('source_event')}",
                            ))
            except Exception:
                pass
        return incidents

    async def _fetch_tidal_anomalies(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch real-time tidal gauge anomalies (storm surge detection)."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.INCOIS_TIDAL_URL, params={"anomaly": "true"})
                if resp.status_code == 200:
                    for gauge in resp.json().get("gauges", []):
                        if gauge.get("anomaly_m", 0) > 0.5:  # > 0.5m anomaly
                            incidents.append(RawIncident(
                                channel_id=self.channel_id,
                                raw_data=gauge,
                                source_id=gauge.get("gauge_id"),
                                latitude=float(gauge.get("latitude", 0)),
                                longitude=float(gauge.get("longitude", 0)),
                                location_text=gauge.get("station_name"),
                                description=f"Tidal anomaly: {gauge.get('anomaly_m')}m above normal at {gauge.get('station_name')}",
                            ))
            except Exception:
                pass
        return incidents

    async def _fetch_storm_surge(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch storm surge warnings from INCOIS."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.INCOIS_TMS_URL, params={"type": "storm_surge"})
                if resp.status_code == 200:
                    for surge in resp.json().get("warnings", []):
                        incidents.append(RawIncident(
                            channel_id=ChannelID.COASTAL_ALERT,
                            raw_data=surge,
                            source_id=surge.get("warning_id"),
                            description=f"Storm surge: {surge.get('surge_height_m')}m — {surge.get('coastal_areas')}",
                        ))
            except Exception:
                pass
        return incidents

    async def normalize(self, raw: RawIncident) -> dict:
        data = raw.raw_data
        level = data.get("level", "").upper()
        severity_map = {"WARNING": "critical", "WATCH": "high", "ADVISORY": "medium", "INFO": "low"}
        return {
            "channel": "early_warning",
            "hazard_type": "tsunami" if "tsunami" in (raw.description or "").lower() else "cyclone",
            "severity": severity_map.get(level, "high"),
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "needs_swarm": level in ("WARNING", "WATCH"),
        }

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://incois.gov.in/tms/api/health")
                return resp.status_code == 200
        except Exception:
            return False
