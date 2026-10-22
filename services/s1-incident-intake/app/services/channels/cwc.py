"""
CWC Adapter - Central Water Commission
======================================

CWC monitors water levels at ~1400 key reservoir sites and provides:
  - Flood forecasts (Level forecast, Inflow forecast)
  - Reservoir level data
  - Dam safety alerts
  - Water storage status

API: CWC provides data through:
  - https://cwc.gov.in/ (flood monitoring dashboard)
  - REST API for flood forecasting (newer)
  - Email/SMS alerts for flood warnings (traditional)

River basins monitored: Ganga, Brahmaputra, Godavari, Krishna, Cauvery, Mahanadi, Narmada, Tapi
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class CWCAdapter(BaseChannelAdapter):
    """CWC flood forecast and reservoir monitoring ingestion."""

    channel_id = ChannelID.CWC

    CWC_FLOOD_URL = "https://cwc.gov.in/api/flood_forecast"
    CWC_RESERVOIR_URL = "https://cwc.gov.in/api/reservoir_level"
    CWC_DAM_ALERT_URL = "https://cwc.gov.in/api/dam_alert"

    # Flood severity thresholds
    DANGER_LEVEL_PCT = 100.0    # At or above danger level
    WARNING_LEVEL_PCT = 90.0    # Approaching danger level

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch CWC flood forecasts + reservoir levels + dam alerts."""
        incidents = []
        errors = []

        try:
            flood = await self._fetch_flood_forecasts(since)
            incidents.extend(flood)
        except Exception as e:
            errors.append(f"flood: {e}")

        try:
            reservoir = await self._fetch_reservoir_levels(since)
            incidents.extend(reservoir)
        except Exception as e:
            errors.append(f"reservoir: {e}")

        try:
            dam = await self._fetch_dam_alerts(since)
            incidents.extend(dam)
        except Exception as e:
            errors.append(f"dam: {e}")

        return FetchResult(
            channel_id=self.channel_id,
            success=len(errors) == 0,
            incidents=incidents,
            error="; ".join(errors) if errors else None,
            fetched_at=datetime.now(timezone.utc),
        )

    async def _fetch_flood_forecasts(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch active flood forecasts from CWC."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {"status": "active"}
                if since:
                    params["since"] = since.isoformat()
                resp = await client.get(self.CWC_FLOOD_URL, params=params)
                if resp.status_code == 200:
                    for forecast in resp.json().get("forecasts", []):
                        level_pct = forecast.get("current_level_pct", 0)
                        severity = "critical" if level_pct >= self.DANGER_LEVEL_PCT else \
                                   "high" if level_pct >= self.WARNING_LEVEL_PCT else "medium"
                        incidents.append(RawIncident(
                            channel_id=ChannelID.FFC,
                            raw_data={**forecast, "severity": severity},
                            source_id=forecast.get("forecast_id"),
                            latitude=float(forecast.get("latitude", 0)),
                            longitude=float(forecast.get("longitude", 0)),
                            location_text=f"{forecast.get('site_name')}, {forecast.get('river')}, {forecast.get('basin')}",
                            description=f"Flood forecast: {forecast.get('site_name')} on {forecast.get('river')} — "
                                       f"Current: {forecast.get('current_level_m')}m ({level_pct:.0f}% of danger level) — "
                                       f"Forecast: {forecast.get('forecast_level_m')}m in {forecast.get('forecast_hours')}h",
                        ))
            except Exception:
                pass
        return incidents

    async def _fetch_reservoir_levels(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch reservoir levels — flag those approaching FRL (Full Reservoir Level)."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.CWC_RESERVOIR_URL, params={"near_frl": "true"})
                if resp.status_code == 200:
                    for reservoir in resp.json().get("reservoirs", []):
                        fill_pct = reservoir.get("current_storage_pct_frl", 0)
                        if fill_pct >= 95:  # Near or at capacity
                            incidents.append(RawIncident(
                                channel_id=self.channel_id,
                                raw_data=reservoir,
                                source_id=reservoir.get("reservoir_id"),
                                latitude=float(reservoir.get("latitude", 0)),
                                longitude=float(reservoir.get("longitude", 0)),
                                location_text=reservoir.get("dam_name"),
                                description=f"Reservoir alert: {reservoir.get('dam_name')} at {fill_pct:.1f}% FRL — "
                                           f"Storage: {reservoir.get('current_storage_mcm')} MCM — "
                                           f"Live capacity: {reservoir.get('live_capacity_mcm')} MCM",
                            ))
            except Exception:
                pass
        return incidents

    async def _fetch_dam_alerts(self, since: Optional[datetime]) -> list[RawIncident]:
        """Fetch dam safety/emergency alerts from CWC."""
        incidents = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.CWC_DAM_ALERT_URL)
                if resp.status_code == 200:
                    for alert in resp.json().get("alerts", []):
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=alert,
                            source_id=alert.get("alert_id"),
                            latitude=float(alert.get("latitude", 0)),
                            longitude=float(alert.get("longitude", 0)),
                            location_text=alert.get("dam_name"),
                            description=f"DAM ALERT: {alert.get('dam_name')} — {alert.get('alert_type')} — {alert.get('message')}",
                        ))
            except Exception:
                pass
        return incidents

    async def normalize(self, raw: RawIncident) -> dict:
        data = raw.raw_data
        return {
            "channel": "early_warning",
            "hazard_type": "flood",
            "severity": data.get("severity", "high"),
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "needs_swarm": data.get("severity") in ("critical", "high"),
        }

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://cwc.gov.in/api/health")
                return resp.status_code == 200
        except Exception:
            return False
