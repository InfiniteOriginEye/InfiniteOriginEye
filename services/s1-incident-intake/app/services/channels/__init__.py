"""
S1 Channel Adapters - Package Init
====================================

Imports and registers all channel adapters.
"""

from .registry import (
    BaseChannelAdapter,
    ChannelID,
    FetchResult,
    HelplineInfo,
    RawIncident,
    HELPLINE_DIRECTORY,
)
from .erss_112 import ERSS112Adapter
from .imd import IMDAdapter
from .incois import INCOISAdapter
from .cwc import CWCAdapter
from .sachet import SachetAdapter
from .social_media import TwitterAdapter, WhatsAppBusinessAdapter
from .citizen_sms import CitizenAppAdapter, SMSAdapter
from .iot_sensors import IoTFloodAdapter, IoTSeismicAdapter, IoTRainGaugeAdapter
from .sector_helplines import (
    RailMadadAdapter,
    StateHelplineAdapter,
    NDRFWhatsAppAdapter,
    CPGRAMSAdapter,
)

# =============================================================================
# ACTIVE ADAPTER REGISTRY — Maps channel IDs → adapter instances
# =============================================================================

ADAPTERS: dict[ChannelID, BaseChannelAdapter] = {
    # National helplines
    ChannelID.ERSS_112: ERSS112Adapter(),
    ChannelID.NDRF: StateHelplineAdapter(ChannelID.NDRF),
    ChannelID.NDMA: StateHelplineAdapter(ChannelID.NDMA),
    ChannelID.MHA_CONTROL: StateHelplineAdapter(ChannelID.MHA_CONTROL),

    # State SEOCs
    ChannelID.SEOC_UTTARAKHAND: StateHelplineAdapter(ChannelID.SEOC_UTTARAKHAND, "Uttarakhand"),
    ChannelID.SEOC_KERALA: StateHelplineAdapter(ChannelID.SEOC_KERALA, "Kerala"),
    ChannelID.SEOC_TAMIL_NADU: StateHelplineAdapter(ChannelID.SEOC_TAMIL_NADU, "Tamil Nadu"),
    ChannelID.SEOC_ASSAM: StateHelplineAdapter(ChannelID.SEOC_ASSAM, "Assam"),
    ChannelID.SEOC_HIMACHAL: StateHelplineAdapter(ChannelID.SEOC_HIMACHAL, "Himachal Pradesh"),

    # Weather & Early Warning (REAL APIs)
    ChannelID.IMD: IMDAdapter(),
    ChannelID.INCOIS: INCOISAdapter(),
    ChannelID.CWC: CWCAdapter(),
    ChannelID.SACHET: SachetAdapter(),

    # Sector helplines
    ChannelID.FIRE_101: StateHelplineAdapter(ChannelID.FIRE_101),
    ChannelID.POLICE_100: StateHelplineAdapter(ChannelID.POLICE_100),
    ChannelID.AMBULANCE_108: StateHelplineAdapter(ChannelID.AMBULANCE_108),
    ChannelID.WOMEN_181: StateHelplineAdapter(ChannelID.WOMEN_181),
    ChannelID.CHILD_1098: StateHelplineAdapter(ChannelID.CHILD_1098),
    ChannelID.SENIOR_CITIZEN_14567: StateHelplineAdapter(ChannelID.SENIOR_CITIZEN_14567),
    ChannelID.MENTAL_HEALTH: StateHelplineAdapter(ChannelID.MENTAL_HEALTH),

    # Disaster-specific
    ChannelID.RAILMADAD: RailMadadAdapter(),
    ChannelID.NDRF_WHATSAPP: NDRFWhatsAppAdapter(),
    ChannelID.EARTHQUAKE_IMD: IMDAdapter(),      # Same IMD adapter, different channel ID
    ChannelID.CYCLONE_IMD: IMDAdapter(),
    ChannelID.COASTAL_ALERT: INCOISAdapter(),

    # Regulatory
    ChannelID.CPGRAMS: CPGRAMSAdapter(),

    # Citizen-facing
    ChannelID.CITIZEN_APP: CitizenAppAdapter(),
    ChannelID.SMS_SHORTCODE: SMSAdapter(),
    ChannelID.WEB_PORTAL: CitizenAppAdapter(),     # Same as citizen app
    ChannelID.SOCIAL_MEDIA: TwitterAdapter(),
    ChannelID.WHATSAPP_BUSINESS: WhatsAppBusinessAdapter(),

    # IoT Sensors
    ChannelID.IOT_FLOOD_SENSOR: IoTFloodAdapter(),
    ChannelID.IOT_SEISMIC: IoTSeismicAdapter(),
    ChannelID.IOT_RAIN_GAUGE: IoTRainGaugeAdapter(),

    # Armed Forces (manual coordination only)
    ChannelID.ARMY: StateHelplineAdapter(ChannelID.ARMY),
    ChannelID.AIRFORCE: StateHelplineAdapter(ChannelID.AIRFORCE),
    ChannelID.NAVY: StateHelplineAdapter(ChannelID.NAVY),
    ChannelID.COASTGUARD: StateHelplineAdapter(ChannelID.COASTGUARD),
    ChannelID.BSF: StateHelplineAdapter(ChannelID.BSF),
    ChannelID.CISF: StateHelplineAdapter(ChannelID.CISF),
    ChannelID.CRPF: StateHelplineAdapter(ChannelID.CRPF),
    ChannelID.SSB: StateHelplineAdapter(ChannelID.SSB),

    # NGO
    ChannelID.RED_CROSS: StateHelplineAdapter(ChannelID.RED_CROSS),
    ChannelID.RDD: StateHelplineAdapter(ChannelID.RDD),
}

# Channels grouped by fetch strategy
POLL_CHANNELS = [cid for cid, info in HELPLINE_DIRECTORY.items() if info.fetch_strategy == "poll"]
WEBHOOK_CHANNELS = [cid for cid, info in HELPLINE_DIRECTORY.items() if info.fetch_strategy == "webhook"]
STREAM_CHANNELS = [cid for cid, info in HELPLINE_DIRECTORY.items() if info.fetch_strategy == "stream"]
MANUAL_CHANNELS = [cid for cid, info in HELPLINE_DIRECTORY.items() if info.fetch_strategy == "manual"]

__all__ = [
    "ADAPTERS", "POLL_CHANNELS", "WEBHOOK_CHANNELS", "STREAM_CHANNELS", "MANUAL_CHANNELS",
    "HELPLINE_DIRECTORY", "ChannelID", "BaseChannelAdapter", "FetchResult", "RawIncident",
]
