# =============================================================================
# S5 - Early-Warning Ingest
# Owner: SDMA / SEOC
# Tech: Python 3.11 + FastAPI + Kafka + PostgreSQL/PostGIS
# Port: 8005
#
# Ingests from:
#   IMD   - India Meteorological Department (weather, cyclone, earthquake)
#   INCOIS - Indian National Centre for Ocean Information (tsunami, storm surge)
#   CWC   - Central Water Commission (flood, dam break)
#   GFS   - Global Forecast System (weather model data)
#   Sachet - NDMA CAP alert platform (unified multi-agency)
# =============================================================================

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
import logging

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx

logger = logging.getLogger("s5.early_warning")

# =============================================================================
# IMD Feed Ingestion
# =============================================================================

class IMDIngestService:
    """IMD weather warning ingestion — poll IMD APIs every 5 minutes."""

    API_BASE = "https://mausam.imd.gov.in/api"
    SACHET_API = "https://sachet.ndma.gov.in/api/alerts"

    SEVERITY_MAP = {"RED": "critical", "ORANGE": "high", "YELLOW": "medium", "GREEN": "low"}

    HAZARD_MAP = {
        "HEAVY RAIN": "flood", "VERY HEAVY RAIN": "flood",
        "EXTREMELY HEAVY RAIN": "cloudburst", "THUNDERSTORM": "other",
        "CYCLONE": "cyclone", "HEAT WAVE": "other", "COLD WAVE": "other",
        "FOG": "other", "LANDSLIDE": "landslide", "EARTHQUAKE": "earthquake",
        "TSUNAMI": "tsunami", "FLOOD": "flood",
    }

    async def fetch_weather_warnings(self, since: Optional[datetime] = None) -> list[dict]:
        """Fetch IMD weather warnings via Sachet CAP feed (preferred) or direct API."""
        alerts = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Preferred: Sachet CAP (structured, multi-language)
            try:
                params = {"source": "IMD"}
                if since:
                    params["since"] = since.isoformat()
                resp = await client.get(self.SACHET_API, params=params)
                if resp.status_code == 200:
                    for alert in resp.json().get("alerts", []):
                        info = alert.get("info", [{}])[0] if alert.get("info") else {}
                        area = info.get("area", [{}])[0] if info.get("area") else {}
                        centroid = area.get("centroid", {})
                        alerts.append({
                            "source": "imd",
                            "alert_id": alert.get("identifier"),
                            "hazard_type": self.HAZARD_MAP.get(
                                (info.get("event") or "").upper(), "other"
                            ),
                            "severity": self.SEVERITY_MAP.get(
                                (info.get("severity") or "YELLOW").upper(), "medium"
                            ),
                            "latitude": centroid.get("lat"),
                            "longitude": centroid.get("lon"),
                            "region": area.get("areaDesc"),
                            "description": info.get("description"),
                            "headline": info.get("headline"),
                            "effective": info.get("effective"),
                            "expires": info.get("expires"),
                            "cap_data": alert,
                        })
                    return alerts
            except Exception as e:
                logger.warning(f"Sachet fetch failed, falling back to direct IMD: {e}")

            # Fallback: Direct IMD API
            try:
                resp = await client.get(f"{self.API_BASE}/weather_warning")
                if resp.status_code == 200:
                    for w in resp.json().get("warnings", []):
                        color = (w.get("color_code") or "YELLOW").upper()
                        alerts.append({
                            "source": "imd",
                            "alert_id": w.get("id"),
                            "hazard_type": self.HAZARD_MAP.get(
                                (w.get("warning_type") or "").upper(), "other"
                            ),
                            "severity": self.SEVERITY_MAP.get(color, "medium"),
                            "latitude": w.get("lat"),
                            "longitude": w.get("lon"),
                            "region": w.get("region"),
                            "description": w.get("warning_text"),
                        })
            except Exception as e:
                logger.error(f"Direct IMD fetch failed: {e}")

        return alerts


class INCOISIngestService:
    """INCOIS tsunami & ocean alert ingestion."""

    TMS_URL = "https://incois.gov.in/tms/api/warnings"
    TIDAL_URL = "https://incois.gov.in/tidal/api/realtime"

    async def fetch_tsunami_warnings(self, since: Optional[datetime] = None) -> list[dict]:
        """Fetch active tsunami warnings from INCOIS TMS."""
        alerts = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.TMS_URL, params={"status": "active"})
                if resp.status_code == 200:
                    for w in resp.json().get("warnings", []):
                        level = (w.get("level") or "").upper()
                        for region in w.get("affected_regions", [{}]):
                            alerts.append({
                                "source": "incois",
                                "alert_id": w.get("warning_id"),
                                "hazard_type": "tsunami",
                                "severity": {"WARNING": "critical", "WATCH": "high"}.get(level, "medium"),
                                "latitude": region.get("lat"),
                                "longitude": region.get("lon"),
                                "region": region.get("coastal_state"),
                                "description": f"Tsunami {level}: {w.get('source_event')} — ETA: {w.get('eta')}",
                            })
            except Exception as e:
                logger.error(f"INCOIS fetch failed: {e}")
        return alerts

    async def fetch_tidal_anomalies(self) -> list[dict]:
        """Fetch tidal gauge anomalies (storm surge indicators)."""
        alerts = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.TIDAL_URL, params={"anomaly": "true"})
                if resp.status_code == 200:
                    for g in resp.json().get("gauges", []):
                        anomaly = g.get("anomaly_m", 0)
                        if anomaly > 0.5:
                            alerts.append({
                                "source": "incois",
                                "alert_id": g.get("gauge_id"),
                                "hazard_type": "cyclone",
                                "severity": "high" if anomaly > 1.0 else "medium",
                                "latitude": g.get("latitude"),
                                "longitude": g.get("longitude"),
                                "region": g.get("station_name"),
                                "description": f"Tidal anomaly: {anomaly}m above normal at {g.get('station_name')}",
                            })
            except Exception as e:
                logger.error(f"Tidal fetch failed: {e}")
        return alerts


class CWCIngestService:
    """CWC flood forecast and reservoir monitoring ingestion."""

    FLOOD_URL = "https://cwc.gov.in/api/flood_forecast"
    RESERVOIR_URL = "https://cwc.gov.in/api/reservoir_level"

    async def fetch_flood_forecasts(self, since: Optional[datetime] = None) -> list[dict]:
        """Fetch active flood forecasts from CWC."""
        alerts = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {"status": "active"}
                if since:
                    params["since"] = since.isoformat()
                resp = await client.get(self.FLOOD_URL, params=params)
                if resp.status_code == 200:
                    for f in resp.json().get("forecasts", []):
                        level_pct = f.get("current_level_pct", 0)
                        severity = "critical" if level_pct >= 100 else "high" if level_pct >= 90 else "medium"
                        alerts.append({
                            "source": "cwc",
                            "alert_id": f.get("forecast_id"),
                            "hazard_type": "flood",
                            "severity": severity,
                            "latitude": f.get("latitude"),
                            "longitude": f.get("longitude"),
                            "region": f"{f.get('site_name')}, {f.get('river')}, {f.get('basin')}",
                            "description": f"Flood forecast: {f.get('site_name')} on {f.get('river')} — "
                                          f"Current: {f.get('current_level_m')}m ({level_pct:.0f}% danger level) — "
                                          f"Forecast: {f.get('forecast_level_m')}m in {f.get('forecast_hours')}h",
                            "river": f.get("river"),
                            "basin": f.get("basin"),
                            "current_level_m": f.get("current_level_m"),
                            "danger_level_m": f.get("danger_level_m"),
                        })
            except Exception as e:
                logger.error(f"CWC flood fetch failed: {e}")
        return alerts

    async def fetch_reservoir_alerts(self) -> list[dict]:
        """Fetch reservoirs near Full Reservoir Level."""
        alerts = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.RESERVOIR_URL, params={"near_frl": "true"})
                if resp.status_code == 200:
                    for r in resp.json().get("reservoirs", []):
                        fill_pct = r.get("current_storage_pct_frl", 0)
                        if fill_pct >= 95:
                            alerts.append({
                                "source": "cwc",
                                "alert_id": r.get("reservoir_id"),
                                "hazard_type": "flood",
                                "severity": "critical" if fill_pct >= 99 else "high",
                                "latitude": r.get("latitude"),
                                "longitude": r.get("longitude"),
                                "region": r.get("dam_name"),
                                "description": f"Reservoir at {fill_pct:.1f}% FRL: {r.get('dam_name')} — "
                                              f"Storage: {r.get('current_storage_mcm')} MCM",
                            })
            except Exception as e:
                logger.error(f"CWC reservoir fetch failed: {e}")
        return alerts


# =============================================================================
# Orchestrator - polls all sources and publishes to Kafka
# =============================================================================

class EarlyWarningOrchestrator:
    """Polls IMD, INCOIS, CWC and publishes alerts to Kafka."""

    def __init__(self, kafka_producer=None):
        self.kafka_producer = kafka_producer
        self.running = False
        self.imd = IMDIngestService()
        self.incois = INCOISIngestService()
        self.cwc = CWCIngestService()
        self.last_fetch: dict[str, datetime] = {}
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        self.running = True
        logger.info("S5 Early-Warning Orchestrator starting")
        self._tasks = [
            asyncio.create_task(self._poll_loop("imd", self._fetch_imd, 300)),
            asyncio.create_task(self._poll_loop("incois_tsunami", self._fetch_incois_tsunami, 600)),
            asyncio.create_task(self._poll_loop("incois_tidal", self._fetch_incois_tidal, 600)),
            asyncio.create_task(self._poll_loop("cwc_flood", self._fetch_cwc_flood, 900)),
            asyncio.create_task(self._poll_loop("cwc_reservoir", self._fetch_cwc_reservoir, 1800)),
        ]

    async def stop(self):
        self.running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _poll_loop(self, name: str, fetch_fn, interval_s: int):
        while self.running:
            try:
                alerts = await fetch_fn()
                if alerts:
                    await self._publish_alerts(name, alerts)
                    logger.info(f"[{name}] {len(alerts)} alerts")
                self.last_fetch[name] = datetime.now(timezone.utc)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{name}] Error: {e}")
            await asyncio.sleep(interval_s)

    async def _fetch_imd(self): return await self.imd.fetch_weather_warnings(self.last_fetch.get("imd"))
    async def _fetch_incois_tsunami(self): return await self.incois.fetch_tsunami_warnings(self.last_fetch.get("incois_tsunami"))
    async def _fetch_incois_tidal(self): return await self.incois.fetch_tidal_anomalies()
    async def _fetch_cwc_flood(self): return await self.cwc.fetch_flood_forecasts(self.last_fetch.get("cwc_flood"))
    async def _fetch_cwc_reservoir(self): return await self.cwc.fetch_reservoir_alerts()

    async def _publish_alerts(self, source: str, alerts: list[dict]):
        """Publish alerts to Kafka 'alerts.early_warning' topic."""
        for alert in alerts:
            alert_data = {
                "alert_id": alert.get("alert_id"),
                "source": alert.get("source"),
                "hazard_type": alert.get("hazard_type"),
                "severity": alert.get("severity"),
                "latitude": alert.get("latitude"),
                "longitude": alert.get("longitude"),
                "region": alert.get("region"),
                "description": alert.get("description"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "should_create_incident": alert.get("severity") in ("critical", "high"),
            }
            if self.kafka_producer:
                import json
                await self.kafka_producer.send(
                    topic="alerts.early_warning",
                    key=alert.get("alert_id", ""),
                    value=json.dumps(alert_data).encode(),
                )
            else:
                logger.debug(f"[{source}] Alert: {alert.get('description', '')[:80]}")

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "sources": {
                "imd": {"interval_s": 300, "last_fetch": self.last_fetch.get("imd", {}).isoformat() if isinstance(self.last_fetch.get("imd"), datetime) else None},
                "incois_tsunami": {"interval_s": 600},
                "incois_tidal": {"interval_s": 600},
                "cwc_flood": {"interval_s": 900},
                "cwc_reservoir": {"interval_s": 1800},
            },
        }


# =============================================================================
# FastAPI App
# =============================================================================

ew_orchestrator = EarlyWarningOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ew_orchestrator.start()
    yield
    await ew_orchestrator.stop()

app = FastAPI(
    title="S5 - Early-Warning Ingest",
    description="IMD/INCOIS/CWC/GFS feed ingestion, threshold analysis, automated alerting",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s5-early-warning"}

@app.get("/api/v1/alerts/status")
async def alerts_status():
    return ew_orchestrator.get_status()

@app.post("/api/v1/alerts/imd/fetch")
async def fetch_imd_now(background_tasks: BackgroundTasks):
    """Force-fetch IMD warnings now (instead of waiting for next poll)."""
    alerts = await ew_orchestrator.imd.fetch_weather_warnings()
    await ew_orchestrator._publish_alerts("imd_manual", alerts)
    return {"source": "imd", "alerts_found": len(alerts)}

@app.post("/api/v1/alerts/incois/fetch")
async def fetch_incois_now():
    """Force-fetch INCOIS tsunami + tidal data now."""
    tsunami = await ew_orchestrator.incois.fetch_tsunami_warnings()
    tidal = await ew_orchestrator.incois.fetch_tidal_anomalies()
    all_alerts = tsunami + tidal
    await ew_orchestrator._publish_alerts("incois_manual", all_alerts)
    return {"source": "incois", "tsunami": len(tsunami), "tidal_anomalies": len(tidal)}

@app.post("/api/v1/alerts/cwc/fetch")
async def fetch_cwc_now():
    """Force-fetch CWC flood forecasts + reservoir levels now."""
    flood = await ew_orchestrator.cwc.fetch_flood_forecasts()
    reservoir = await ew_orchestrator.cwc.fetch_reservoir_alerts()
    all_alerts = flood + reservoir
    await ew_orchestrator._publish_alerts("cwc_manual", all_alerts)
    return {"source": "cwc", "flood_forecasts": len(flood), "reservoir_alerts": len(reservoir)}
