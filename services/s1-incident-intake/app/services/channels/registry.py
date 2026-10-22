"""
S1 Channel Adapters - Registry & Base Classes
==============================================

Every Indian helpline/disaster channel implements BaseChannelAdapter.
The registry maps channel names → adapter instances for S1 to consume.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# CHANNEL REGISTRY - All Indian Disaster Helplines
# =============================================================================

class ChannelID(str, Enum):
    """Every possible intake channel for disaster incidents in India."""

    # --- National Helplines ---
    ERSS_112 = "erss_112"                    # Emergency Response Support System (112)
    NDRF = "ndrf"                            # NDRF control room (011-26144044)
    NDMA = "ndma"                            # NDMA helpline (011-1078)
    MHA_CONTROL = "mha_control"              # MHA Emergency Control Room

    # --- State Emergency Operations Centers ---
    SEOC_UTTARAKHAND = "seoc_uttarakhand"
    SEOC_KERALA = "seoc_kerala"
    SEOC_TAMIL_NADU = "seoc_tamil_nadu"
    SEOC_ASSAM = "seoc_assam"
    SEOC_HIMACHAL = "seoc_himachal"

    # --- Weather & Early Warning ---
    IMD = "imd"                              # India Meteorological Department
    INCOIS = "incois"                        # Indian National Centre for Ocean Information
    CWC = "cwc"                              # Central Water Commission (flood)
    FFC = "ffc"                              # Flood Forecasting Circles

    # --- Sector-Specific Helplines ---
    FIRE_101 = "fire_101"                    # Fire Service (101)
    POLICE_100 = "police_100"                # Police (100)
    AMBULANCE_108 = "ambulance_108"          # Ambulance (108) - EMRI
    WOMEN_181 = "women_181"                  # Women helpline (181)
    CHILD_1098 = "child_1098"               # Child helpline (1098)
    SENIOR_CITIZEN_14567 = "senior_14567"   # Senior citizen (14567)
    MENTAL_HEALTH = "mental_health"          # KIRAN mental health (1800-599-0019)

    # --- Disaster-Specific Helplines ---
    SACHET = "sachet"                        # NDMA Sachet alert platform
    RAILMADAD = "railmadad"                  # Railway helpline (139)
    NDRF_WHATSAPP = "ndrf_whatsapp"          # NDRF WhatsApp (917566363636)
    COASTAL_ALERT = "coastal_alert"          # INCOIS coastal alert
    EARTHQUAKE_IMD = "earthquake_imd"        # IMD earthquake reporting
    CYCLONE_IMD = "cyclone_imd"             # IMD cyclone warning

    # --- Regulatory & Reporting ---
    CPGRAMS = "cpgrams"                      # Centralized Public Grievance (CPGRAMS)
    NDMIS = "ndmis"                          # National Disaster Mgmt Info System
    NIC_ALERT = "nic_alert"                  # NIC emergency alert system

    # --- Citizen-Facing ---
    CITIZEN_APP = "citizen_app"              # S10 Citizen App
    SMS_SHORTCODE = "sms_shortcode"          # SMS to shortcode
    WEB_PORTAL = "web_portal"                # Web reporting portal
    SOCIAL_MEDIA = "social_media"            # Twitter/WhatsApp/Facebook
    WHATSAPP_BUSINESS = "whatsapp_business"  # WhatsApp Business API

    # --- IoT & Sensor ---
    IOT_FLOOD_SENSOR = "iot_flood_sensor"    # IoT flood gauges
    IOT_SEISMIC = "iot_seismic"              # IoT seismic sensors
    IOT_RAIN_GAUGE = "iot_rain_gauge"        # IoT rain gauges

    # --- Partner Agencies ---
    ARMY = "army"                            # Indian Army (HADR)
    AIRFORCE = "airforce"                    # Indian Air Force (HADR)
    NAVY = "navy"                            # Indian Navy (HADR)
    COASTGUARD = "coastguard"                # Indian Coast Guard
    BSF = "bsf"                              # Border Security Force
    CISF = "cisf"                            # Central Industrial Security Force
    CRPF = "crpf"                            # Central Reserve Police Force
    SSB = "ssb"                              # Sashastra Seema Bal

    # --- NGO & Volunteer ---
    RED_CROSS = "red_cross"                  # Indian Red Cross
    RDD = "rdd"                              # Rapid Disaster Response (NGO)


# =============================================================================
# HELPLINE DIRECTORY - Complete reference with phone numbers
# =============================================================================

class HelplineInfo(BaseModel):
    """Complete info about an Indian disaster helpline."""
    channel_id: ChannelID
    name: str
    number: Optional[str] = None
    alt_number: Optional[str] = None
    operator: str                            # Agency that operates it
    scope: str                               # "national", "state", "district"
    coverage: list[str] = Field(default_factory=list)  # States covered (if state-specific)
    available_24x7: bool = True
    api_available: bool = False              # Whether programmatic API exists
    api_type: Optional[str] = None           # "rest", "soap", "websocket", "mqtt", "email"
    api_endpoint: Optional[str] = None
    fetch_strategy: str = "poll"             # "poll", "webhook", "stream", "manual"
    poll_interval_s: int = 300               # How often to poll (seconds)
    priority: int = 1                        # 1=highest (national), 5=lowest (social media)
    notes: str = ""


HELPLINE_DIRECTORY: dict[ChannelID, HelplineInfo] = {
    # --- National ---
    ChannelID.ERSS_112: HelplineInfo(
        channel_id=ChannelID.ERSS_112, name="ERSS/112 Emergency Helpline",
        number="112", operator="MHA/State PSAP", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="webhook",
        priority=1, notes="State-centric PSAP with CAD/GIS. No public API — requires official MoU."
    ),
    ChannelID.NDRF: HelplineInfo(
        channel_id=ChannelID.NDRF, name="NDRF Control Room",
        number="011-26144044", operator="NDRF HQ", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="manual",
        priority=1, notes="NDRF operations control room. Voice calls + fax."
    ),
    ChannelID.NDMA: HelplineInfo(
        channel_id=ChannelID.NDMA, name="NDMA Helpline",
        number="1078", operator="NDMA", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="poll",
        priority=1, notes="NDMA toll-free for disaster info."
    ),
    ChannelID.MHA_CONTROL: HelplineInfo(
        channel_id=ChannelID.MHA_CONTROL, name="MHA Emergency Control Room",
        number="011-23093144", operator="MHA", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="manual",
        priority=1
    ),

    # --- SEOCs (Pilot States) ---
    ChannelID.SEOC_UTTARAKHAND: HelplineInfo(
        channel_id=ChannelID.SEOC_UTTARAKHAND, name="Uttarakhand SEOC",
        number="0135-2714400", operator="USDMA", scope="state",
        coverage=["Uttarakhand"], available_24x7=True,
        api_available=False, fetch_strategy="webhook", priority=1
    ),
    ChannelID.SEOC_KERALA: HelplineInfo(
        channel_id=ChannelID.SEOC_KERALA, name="Kerala SEOC",
        number="0471-2338111", operator="KSDMA", scope="state",
        coverage=["Kerala"], available_24x7=True,
        api_available=False, fetch_strategy="webhook", priority=1
    ),
    ChannelID.SEOC_TAMIL_NADU: HelplineInfo(
        channel_id=ChannelID.SEOC_TAMIL_NADU, name="Tamil Nadu SEOC",
        number="044-22252110", operator="TNSDMA", scope="state",
        coverage=["Tamil Nadu"], available_24x7=True,
        api_available=False, fetch_strategy="webhook", priority=1
    ),
    ChannelID.SEOC_ASSAM: HelplineInfo(
        channel_id=ChannelID.SEOC_ASSAM, name="Assam SEOC",
        number="0361-2226988", operator="ASDMA", scope="state",
        coverage=["Assam"], available_24x7=True,
        api_available=False, fetch_strategy="webhook", priority=1
    ),
    ChannelID.SEOC_HIMACHAL: HelplineInfo(
        channel_id=ChannelID.SEOC_HIMACHAL, name="Himachal Pradesh SEOC",
        number="0177-2626666", operator="HPSDMA", scope="state",
        coverage=["Himachal Pradesh"], available_24x7=True,
        api_available=False, fetch_strategy="webhook", priority=1
    ),

    # --- Weather & Early Warning ---
    ChannelID.IMD: HelplineInfo(
        channel_id=ChannelID.IMD, name="India Meteorological Department",
        number="011-24619944", operator="IMD/MoES", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        api_endpoint="https://mausam.imd.gov.in/api",
        fetch_strategy="poll", poll_interval_s=300, priority=1,
        notes="IMD has REST APIs for weather warnings, cyclone, earthquake alerts."
    ),
    ChannelID.INCOIS: HelplineInfo(
        channel_id=ChannelID.INCOIS, name="INCOIS (Ocean Services)",
        number="040-23895011", operator="INCOIS/MoES", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        api_endpoint="https://incois.gov.in/tms",
        fetch_strategy="poll", poll_interval_s=600, priority=1,
        notes="Tsunami & ocean state alerts. REST API for tidal gauges."
    ),
    ChannelID.CWC: HelplineInfo(
        channel_id=ChannelID.CWC, name="Central Water Commission",
        number="011-24734121", operator="CWC/MoWR", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        fetch_strategy="poll", poll_interval_s=900, priority=1,
        notes="Flood forecasting APIs for major river basins."
    ),
    ChannelID.FFC: HelplineInfo(
        channel_id=ChannelID.FFC, name="Flood Forecasting Circles",
        operator="CWC/MoWR", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="poll",
        poll_interval_s=900, priority=2
    ),

    # --- Sector-Specific ---
    ChannelID.FIRE_101: HelplineInfo(
        channel_id=ChannelID.FIRE_101, name="Fire & Rescue Service",
        number="101", operator="State Fire Services", scope="state",
        available_24x7=True, api_available=False, fetch_strategy="webhook",
        priority=2, notes="Varies by state. Integrated with ERSS in some states."
    ),
    ChannelID.POLICE_100: HelplineInfo(
        channel_id=ChannelID.POLICE_100, name="Police Control Room",
        number="100", operator="State Police", scope="state",
        available_24x7=True, api_available=False, fetch_strategy="webhook",
        priority=2, notes="Integrated with ERSS/112 in most states."
    ),
    ChannelID.AMBULANCE_108: HelplineInfo(
        channel_id=ChannelID.AMBULANCE_108, name="108 Ambulance (EMRI)",
        number="108", operator="GVK EMRI / State Health", scope="state",
        available_24x7=True, api_available=False, fetch_strategy="webhook",
        priority=2, notes="Emergency Medical Research Institute. Major states."
    ),
    ChannelID.WOMEN_181: HelplineInfo(
        channel_id=ChannelID.WOMEN_181, name="Women Helpline (181)",
        number="181", operator="State WCD", scope="state",
        available_24x7=True, api_available=False, fetch_strategy="poll",
        priority=3
    ),
    ChannelID.CHILD_1098: HelplineInfo(
        channel_id=ChannelID.CHILD_1098, name="Child Helpline (1098)",
        number="1098", operator="CHILDLINE India Foundation", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="poll",
        priority=3
    ),
    ChannelID.SENIOR_CITIZEN_14567: HelplineInfo(
        channel_id=ChannelID.SENIOR_CITIZEN_14567, name="Senior Citizen Helpline",
        number="14567", operator="NCSUIR/State", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="poll",
        priority=4
    ),
    ChannelID.MENTAL_HEALTH: HelplineInfo(
        channel_id=ChannelID.MENTAL_HEALTH, name="KIRAN Mental Health",
        number="1800-599-0019", operator="MoHFW", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="poll",
        priority=4
    ),

    # --- Disaster-Specific ---
    ChannelID.SACHET: HelplineInfo(
        channel_id=ChannelID.SACHET, name="Sachet Alert Platform",
        operator="NDMA", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        api_endpoint="https://sachet.ndma.gov.in",
        fetch_strategy="poll", poll_interval_s=60, priority=1,
        notes="NDMA's Cap-based alert platform. REST API for CAP alerts."
    ),
    ChannelID.RAILMADAD: HelplineInfo(
        channel_id=ChannelID.RAILMADAD, name="RailMadad (139)",
        number="139", operator="Indian Railways", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        fetch_strategy="poll", poll_interval_s=300, priority=2,
        notes="Railway grievance + emergency. API for rail incidents."
    ),
    ChannelID.NDRF_WHATSAPP: HelplineInfo(
        channel_id=ChannelID.NDRF_WHATSAPP, name="NDRF WhatsApp",
        number="917566363636", operator="NDRF", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        fetch_strategy="webhook", priority=2,
        notes="WhatsApp Business API for citizen disaster reports."
    ),
    ChannelID.COASTAL_ALERT: HelplineInfo(
        channel_id=ChannelID.COASTAL_ALERT, name="INCOIS Coastal Alert",
        operator="INCOIS", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        fetch_strategy="poll", poll_interval_s=600, priority=1
    ),
    ChannelID.EARTHQUAKE_IMD: HelplineInfo(
        channel_id=ChannelID.EARTHQUAKE_IMD, name="IMD Earthquake Alert",
        operator="IMD", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        api_endpoint="https://seismo.gov.in",
        fetch_strategy="poll", poll_interval_s=60, priority=1,
        notes="IMD seismic monitoring. Real-time earthquake alerts."
    ),
    ChannelID.CYCLONE_IMD: HelplineInfo(
        channel_id=ChannelID.CYCLONE_IMD, name="IMD Cyclone Warning",
        operator="IMD/Regional Meteorological Centre", scope="national",
        available_24x7=True, api_available=True, api_type="rest",
        fetch_strategy="poll", poll_interval_s=300, priority=1,
        notes="Cyclone warnings for Bay of Bengal & Arabian Sea."
    ),

    # --- Regulatory ---
    ChannelID.CPGRAMS: HelplineInfo(
        channel_id=ChannelID.CPGRAMS, name="CPGRAMS",
        operator="DARPG", scope="national",
        api_available=True, api_type="rest",
        fetch_strategy="poll", poll_interval_s=3600, priority=3,
        notes="Centralized Public Grievance Redress and Monitoring System."
    ),
    ChannelID.NDMIS: HelplineInfo(
        channel_id=ChannelID.NDMIS, name="NDMIS",
        operator="NDMA", scope="national",
        api_available=True, api_type="rest",
        fetch_strategy="poll", poll_interval_s=3600, priority=2,
        notes="National Disaster Management Information System."
    ),

    # --- Citizen-Facing ---
    ChannelID.CITIZEN_APP: HelplineInfo(
        channel_id=ChannelID.CITIZEN_APP, name="SC&C Citizen App",
        operator="NDMA/SDMA", scope="national",
        api_available=True, api_type="rest",
        api_endpoint="/api/v1/incidents", fetch_strategy="webhook",
        priority=2, notes="Our own S10 citizen app — primary intake."
    ),
    ChannelID.SMS_SHORTCODE: HelplineInfo(
        channel_id=ChannelID.SMS_SHORTCODE, name="SMS Shortcode",
        operator="SC&C", scope="national",
        api_available=True, api_type="webhook",
        fetch_strategy="webhook", priority=2,
        notes="SMS gateway webhook (e.g., 51969 or custom shortcode)."
    ),
    ChannelID.WEB_PORTAL: HelplineInfo(
        channel_id=ChannelID.WEB_PORTAL, name="Web Reporting Portal",
        operator="SC&C", scope="national",
        api_available=True, api_type="rest",
        api_endpoint="/api/v1/incidents/web", fetch_strategy="webhook",
        priority=2
    ),
    ChannelID.SOCIAL_MEDIA: HelplineInfo(
        channel_id=ChannelID.SOCIAL_MEDIA, name="Social Media Monitor",
        operator="SC&C", scope="national",
        api_available=True, api_type="rest",
        fetch_strategy="stream", poll_interval_s=30, priority=3,
        notes="Twitter API + WhatsApp Business API + Facebook Webhook."
    ),
    ChannelID.WHATSAPP_BUSINESS: HelplineInfo(
        channel_id=ChannelID.WHATSAPP_BUSINESS, name="WhatsApp Business API",
        operator="SC&C", scope="national",
        api_available=True, api_type="rest",
        fetch_strategy="webhook", priority=2,
        notes="WhatsApp Cloud API for citizen reports with images."
    ),

    # --- IoT Sensors ---
    ChannelID.IOT_FLOOD_SENSOR: HelplineInfo(
        channel_id=ChannelID.IOT_FLOOD_SENSOR, name="IoT Flood Sensors",
        operator="CWC/State WRD", scope="state",
        api_available=True, api_type="mqtt",
        fetch_strategy="stream", poll_interval_s=60, priority=2,
        notes="MQTT-streamed water level data from automated gauges."
    ),
    ChannelID.IOT_SEISMIC: HelplineInfo(
        channel_id=ChannelID.IOT_SEISMIC, name="IoT Seismic Sensors",
        operator="IMD/NCS", scope="national",
        api_available=True, api_type="mqtt",
        fetch_strategy="stream", poll_interval_s=10, priority=1,
        notes="Real-time seismic data from IMD/NCS network."
    ),
    ChannelID.IOT_RAIN_GAUGE: HelplineInfo(
        channel_id=ChannelID.IOT_RAIN_GAUGE, name="IoT Rain Gauges",
        operator="IMD/State", scope="state",
        api_available=True, api_type="mqtt",
        fetch_strategy="stream", poll_interval_s=300, priority=2,
        notes="AWS (Automatic Weather Station) rain data via MQTT."
    ),

    # --- Armed Forces ---
    ChannelID.ARMY: HelplineInfo(
        channel_id=ChannelID.ARMY, name="Indian Army HADR",
        operator="Indian Army", scope="national",
        api_available=False, fetch_strategy="manual", priority=1,
        notes="Humanitarian Assistance & Disaster Relief. Manual coordination."
    ),
    ChannelID.AIRFORCE: HelplineInfo(
        channel_id=ChannelID.AIRFORCE, name="IAF HADR",
        operator="Indian Air Force", scope="national",
        api_available=False, fetch_strategy="manual", priority=1,
        notes="Air Force HADR. Manual ops coordination."
    ),
    ChannelID.NAVY: HelplineInfo(
        channel_id=ChannelID.NAVY, name="Indian Navy HADR",
        operator="Indian Navy", scope="national",
        api_available=False, fetch_strategy="manual", priority=1,
        notes="Naval HADR for coastal disasters."
    ),
    ChannelID.COASTGUARD: HelplineInfo(
        channel_id=ChannelID.COASTGUARD, name="Indian Coast Guard",
        number="1800-437-2424", operator="ICG", scope="national",
        available_24x7=True, api_available=False, fetch_strategy="manual",
        priority=1, notes="Maritime search & rescue."
    ),

    # --- CAPF ---
    ChannelID.BSF: HelplineInfo(
        channel_id=ChannelID.BSF, name="BSF", operator="BSF/MHA",
        scope="national", api_available=False, fetch_strategy="manual", priority=2
    ),
    ChannelID.CISF: HelplineInfo(
        channel_id=ChannelID.CISF, name="CISF", operator="CISF/MHA",
        scope="national", api_available=False, fetch_strategy="manual", priority=2
    ),
    ChannelID.CRPF: HelplineInfo(
        channel_id=ChannelID.CRPF, name="CRPF", operator="CRPF/MHA",
        scope="national", api_available=False, fetch_strategy="manual", priority=2
    ),
    ChannelID.SSB: HelplineInfo(
        channel_id=ChannelID.SSB, name="SSB", operator="SSB/MHA",
        scope="national", api_available=False, fetch_strategy="manual", priority=2
    ),

    # --- NGO ---
    ChannelID.RED_CROSS: HelplineInfo(
        channel_id=ChannelID.RED_CROSS, name="Indian Red Cross",
        operator="IRCS", scope="national",
        api_available=False, fetch_strategy="poll", priority=3
    ),
    ChannelID.RDD: HelplineInfo(
        channel_id=ChannelID.RDD, name="Rapid Disaster Response",
        operator="RDD/NGO", scope="national",
        api_available=False, fetch_strategy="manual", priority=3
    ),
}


# =============================================================================
# BASE CHANNEL ADAPTER
# =============================================================================

class RawIncident(BaseModel):
    """Raw incident data fetched from a channel before normalization."""
    channel_id: ChannelID
    raw_data: dict[str, Any]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    source_id: Optional[str] = None          # ID in the source system
    caller_phone: Optional[str] = None
    caller_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_text: Optional[str] = None      # Free-text location
    description: Optional[str] = None
    media_urls: list[str] = Field(default_factory=list)
    timestamp: Optional[datetime] = None      # When the incident was reported


class FetchResult(BaseModel):
    """Result of fetching from a channel."""
    channel_id: ChannelID
    success: bool
    incidents: list[RawIncident] = Field(default_factory=list)
    error: Optional[str] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    next_poll_after: Optional[datetime] = None


class BaseChannelAdapter(ABC):
    """
    Abstract base for all channel adapters.

    Every helpline/data source implements this interface:
      - fetch(): Pull new incidents from the source
      - normalize(): Convert raw data → canonical Incident format
      - send_alert(): Push alerts back to the source (if supported)
    """

    channel_id: ChannelID
    info: HelplineInfo

    def __init__(self):
        self.info = HELPLINE_DIRECTORY.get(self.channel_id)

    @abstractmethod
    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Fetch new incidents from this channel since the given timestamp."""
        ...

    @abstractmethod
    async def normalize(self, raw: RawIncident) -> dict[str, Any]:
        """Normalize raw incident data into canonical Incident fields."""
        ...

    async def send_alert(self, incident_id: str, message: str) -> bool:
        """Send an alert/notification back to this channel (optional)."""
        return False

    async def health_check(self) -> bool:
        """Check if this channel is reachable."""
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} channel={self.channel_id.value}>"
