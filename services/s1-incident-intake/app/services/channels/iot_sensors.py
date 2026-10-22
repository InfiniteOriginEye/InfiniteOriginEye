"""
IoT Sensor Adapter - Flood, Seismic, and Rain Gauge Sensors
============================================================

IoT sensors stream data via MQTT to our EMQX broker:
  - Flood sensors: Water level gauges (CWC, State WRD)
  - Seismic sensors: Accelerometers (IMD/NCS network)
  - Rain gauges: Automatic Weather Stations (IMD)

MQTT Topics:
  scc/iot/flood/{sensor_id}     - Water level (meters, every 1 min)
  scc/iot/seismic/{sensor_id}   - Peak ground acceleration (every 1 sec)
  scc/iot/rain/{sensor_id}      - Rainfall (mm/hr, every 5 min)
"""

from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class IoTFloodAdapter(BaseChannelAdapter):
    """IoT flood sensor ingestion via MQTT stream."""

    channel_id = ChannelID.IOT_FLOOD_SENSOR

    # Threshold levels for alerting
    WARNING_LEVEL_M = 5.0     # Above this → warning
    DANGER_LEVEL_M = 7.0     # Above this → critical
    RAPID_RISE_M_PER_HR = 0.5  # > 0.5m/hr rise → flash flood alert

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """
        IoT sensors stream via MQTT — we don't poll.
        This processes MQTT messages that the worker has buffered.
        """
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def process_mqtt_message(self, sensor_id: str, payload: dict) -> Optional[RawIncident]:
        """Process a single MQTT message from a flood sensor."""
        water_level = payload.get("water_level_m")
        if water_level is None:
            return None

        # Check thresholds
        if water_level >= self.DANGER_LEVEL_M:
            severity = "critical"
        elif water_level >= self.WARNING_LEVEL_M:
            severity = "high"
        else:
            return None  # Below warning — no incident

        # Check for rapid rise (flash flood indicator)
        rise_rate = payload.get("rise_rate_m_per_hr", 0)
        is_flash_flood = rise_rate > self.RAPID_RISE_M_PER_HR

        return RawIncident(
            channel_id=self.channel_id,
            raw_data=payload,
            source_id=sensor_id,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            location_text=payload.get("site_name", sensor_id),
            description=f"{'FLASH FLOOD: ' if is_flash_flood else ''}Water level: {water_level}m "
                       f"({'DANGER' if severity == 'critical' else 'WARNING'} level) "
                       f"at {payload.get('site_name', sensor_id)}"
                       f"{f' — Rising at {rise_rate}m/hr!' if is_flash_flood else ''}",
        )

    async def normalize(self, raw: RawIncident) -> dict:
        data = raw.raw_data
        is_flash = "FLASH FLOOD" in (raw.description or "")
        return {
            "channel": "iot_sensor",
            "hazard_type": "flood" if not is_flash else "cloudburst",
            "severity": "critical" if data.get("water_level_m", 0) >= self.DANGER_LEVEL_M else "high",
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "needs_swarm": True,  # Flood at danger level → deploy swarm
        }


class IoTSeismicAdapter(BaseChannelAdapter):
    """IoT seismic sensor ingestion via MQTT stream."""

    channel_id = ChannelID.IOT_SEISMIC

    # Thresholds
    PGA_WARNING = 0.01   # 1%g — felt, minor
    PGA_ALERT = 0.05     # 5%g — significant
    PGA_CRITICAL = 0.10  # 10%g — major earthquake

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def process_mqtt_message(self, sensor_id: str, payload: dict) -> Optional[RawIncident]:
        """Process seismic sensor MQTT message."""
        pga = payload.get("pga_g")  # Peak Ground Acceleration in g
        if pga is None or pga < self.PGA_WARNING:
            return None

        severity = "critical" if pga >= self.PGA_CRITICAL else \
                   "high" if pga >= self.PGA_ALERT else "medium"

        return RawIncident(
            channel_id=self.channel_id,
            raw_data=payload,
            source_id=sensor_id,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            location_text=payload.get("site_name", sensor_id),
            description=f"Seismic event: PGA={pga*100:.1f}%g at {payload.get('site_name', sensor_id)} — "
                       f"Magnitude estimate: ~{payload.get('estimated_magnitude', '?')}",
        )

    async def normalize(self, raw: RawIncident) -> dict:
        return {
            "channel": "iot_sensor",
            "hazard_type": "earthquake",
            "severity": "critical" if raw.raw_data.get("pga_g", 0) >= self.PGA_CRITICAL else "high",
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "summary_text": raw.description,
            "needs_swarm": raw.raw_data.get("pga_g", 0) >= self.PGA_ALERT,
        }


class IoTRainGaugeAdapter(BaseChannelAdapter):
    """IoT rain gauge ingestion via MQTT stream."""

    channel_id = ChannelID.IOT_RAIN_GAUGE

    # IMD rainfall intensity thresholds
    HEAVY_RAIN_MM_HR = 64.5       # Heavy: > 64.5 mm/hr
    VERY_HEAVY_RAIN_MM_HR = 115.5  # Very heavy: > 115.5 mm/hr
    EXTREME_RAIN_MM_HR = 204.5     # Extremely heavy: > 204.5 mm/hr

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def process_mqtt_message(self, sensor_id: str, payload: dict) -> Optional[RawIncident]:
        """Process rain gauge MQTT message."""
        rainfall = payload.get("rainfall_mm_hr")
        if rainfall is None or rainfall < self.HEAVY_RAIN_MM_HR:
            return None

        if rainfall >= self.EXTREME_RAIN_MM_HR:
            category, severity = "Extremely Heavy", "critical"
        elif rainfall >= self.VERY_HEAVY_RAIN_MM_HR:
            category, severity = "Very Heavy", "high"
        else:
            category, severity = "Heavy", "medium"

        return RawIncident(
            channel_id=self.channel_id,
            raw_data=payload,
            source_id=sensor_id,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            location_text=payload.get("site_name", sensor_id),
            description=f"{category} rainfall: {rainfall:.1f} mm/hr at {payload.get('site_name', sensor_id)}",
        )

    async def normalize(self, raw: RawIncident) -> dict:
        rainfall = raw.raw_data.get("rainfall_mm_hr", 0)
        is_extreme = rainfall >= self.EXTREME_RAIN_MM_HR
        return {
            "channel": "iot_sensor",
            "hazard_type": "cloudburst" if is_extreme else "flood",
            "severity": "critical" if is_extreme else "high",
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "summary_text": raw.description,
            "needs_swarm": is_extreme,
        }
