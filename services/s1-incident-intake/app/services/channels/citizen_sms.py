"""
Citizen App & SMS Adapter
==========================

S10 Citizen App: Primary intake from our own citizen-facing mobile app.
SMS Shortcode: SMS gateway webhook (e.g., 51969 for NDMA, custom shortcode).

These are our own channels — full control, REST API, webhook-based.
"""

from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


class CitizenAppAdapter(BaseChannelAdapter):
    """Our S10 Citizen App — primary intake channel with full API control."""

    channel_id = ChannelID.CITIZEN_APP

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Citizen app is webhook-based — incidents come in via POST /api/v1/incidents."""
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def normalize(self, raw: RawIncident) -> dict:
        """Citizen app sends structured data — minimal normalization needed."""
        data = raw.raw_data
        return {
            "channel": "citizen_app",
            "reporter_name": data.get("reporter_name"),
            "reporter_phone": data.get("reporter_phone"),
            "contact_consent": data.get("contact_consent", False),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "accuracy_m": data.get("accuracy_m"),
            "landmark": data.get("landmark"),
            "hazard_type": data.get("hazard_type", "other"),
            "severity": data.get("severity", "medium"),
            "summary_text": data.get("description"),
            "media_urls": data.get("media_urls", []),
            "needs_swarm": False,  # AI triage decides
        }


class SMSAdapter(BaseChannelAdapter):
    """SMS Shortcode gateway — webhook-based intake from SMS providers."""

    channel_id = ChannelID.SMS_SHORTCODE

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """SMS is webhook-based — incoming SMS trigger our webhook endpoint."""
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def process_inbound_sms(self, sender: str, text: str, timestamp: datetime) -> RawIncident:
        """
        Process an inbound SMS message.

        Format: DISASTER <type> <location> <description>
        Example: DISASTER flood Rudraprayag highway landslide 50 vehicles trapped
        Simple format: Just free-text — AI will parse
        """
        return RawIncident(
            channel_id=self.channel_id,
            raw_data={"sender": sender, "text": text},
            caller_phone=sender,
            description=text,
            timestamp=timestamp,
        )

    async def normalize(self, raw: RawIncident) -> dict:
        return {
            "channel": "sms_shortcode",
            "reporter_phone": raw.caller_phone,
            "hazard_type": "other",  # AI parses SMS text
            "severity": "medium",
            "summary_text": raw.raw_data.get("text"),
            "needs_swarm": False,
        }

    async def send_alert(self, incident_id: str, message: str) -> bool:
        """Send outbound SMS to the reporter or 112 operator."""
        # Implementation: Call SMS gateway API (e.g., MSG91, Twilio, BSNL)
        return True
