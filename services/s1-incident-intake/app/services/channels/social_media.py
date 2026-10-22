"""
Social Media & WhatsApp Adapter
================================

Monitors social media for disaster-related content:
  - Twitter/X API v2: Stream tweets with disaster keywords
  - WhatsApp Business API: Webhook for citizen reports
  - Facebook Webhook: Page messages mentioning disasters

Keywords in English + Hindi + regional languages for pilot states.
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from .registry import BaseChannelAdapter, ChannelID, FetchResult, RawIncident


# Disaster keywords for social media monitoring (multilingual)
DISASTER_KEYWORDS = {
    "english": [
        "flood", "landslide", "earthquake", "cyclone", "fire", "rescue",
        "trapped", "stranded", "help", "emergency", "disaster", "drowning",
        "collapsed", "cloudburst", "avalanche", "dam break",
    ],
    "hindi": [
        "बाढ़",       # flood
        "भूस्खलन",     # landslide
        "भूकंप",       # earthquake
        "चक्रवात",     # cyclone
        "आग",         # fire
        "बचाव",        # rescue
        "फंसे",        # trapped
        "मदद",         # help
        "आपातकालीन",   # emergency
        "आपदा",        # disaster
        "बादल फटना",   # cloudburst
        "हिमस्खलन",    # avalanche
    ],
    "malayalam": ["വെള്ളപ്പൊക്കൽ", "മണ്ണിടിഞ്ഞു", "ഭൂകമ്പം"],  # flood, landslide, earthquake
    "tamil": ["வெள்ளம்", "நிலச்சரிவு", "நிலநடுக்கம்"],
    "assamese": ["বান", "ভূমিকম্প"],
    "kannada": ["ಪ್ರವಾಹ", "ಭೂಕಂಪ"],
}


class TwitterAdapter(BaseChannelAdapter):
    """Twitter/X API v2 streaming for disaster-related tweets."""

    channel_id = ChannelID.SOCIAL_MEDIA

    TWITTER_STREAM_URL = "https://api.twitter.com/2/tweets/search/stream"
    TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

    def __init__(self, bearer_token: Optional[str] = None):
        super().__init__()
        self.bearer_token = bearer_token

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """Search recent tweets with disaster keywords."""
        if not self.bearer_token:
            return FetchResult(
                channel_id=self.channel_id, success=False,
                error="No- Twitter bearer token not configured",
                fetched_at=datetime.now(timezone.utc),
            )

        incidents = []
        keywords = []
        for lang_keywords in DISASTER_KEYWORDS.values():
            keywords.extend(lang_keywords)

        query = " OR ".join(f'"{kw}"' for kw in keywords[:20])  # Twitter query limit
        query += " -is:retweet -is:reply"  # Filter noise

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    self.TWITTER_SEARCH_URL,
                    params={
                        "query": query,
                        "max_results": 50,
                        "tweet.fields": "created_at,geo,author_id,entities",
                    },
                    headers={"Authorization": f"Bearer {self.bearer_token}"},
                )
                if resp.status_code == 200:
                    for tweet in resp.json().get("data", []):
                        geo = tweet.get("geo", {})
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=tweet,
                            source_id=tweet.get("id"),
                            caller_phone=None,
                            description=tweet.get("text"),
                            latitude=geo.get("coordinates", {}).get("latitude") if geo else None,
                            longitude=geo.get("coordinates", {}).get("longitude") if geo else None,
                            timestamp=datetime.fromisoformat(tweet["created_at"]) if "created_at" in tweet else None,
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
            "channel": "social_media",
            "hazard_type": "other",  # AI will classify from text
            "severity": "medium",
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "summary_text": raw.description,
            "needs_swarm": False,  # AI triage must confirm
        }


class WhatsAppBusinessAdapter(BaseChannelAdapter):
    """WhatsApp Business API webhook for citizen disaster reports."""

    channel_id = ChannelID.WHATSAPP_BUSINESS

    # WhatsApp Cloud API
    VERIFY_TOKEN = None   # Set from env
    ACCESS_TOKEN = None   # Set from env
    PHONE_NUMBER_ID = None  # Set from env

    async def fetch(self, since: Optional[datetime] = None) -> FetchResult:
        """
        WhatsApp is webhook-based — we don't poll.
        This method processes incoming webhook payloads stored in our queue.
        """
        # Webhook payloads are stored by the webhook endpoint and processed here
        return FetchResult(
            channel_id=self.channel_id, success=True,
            incidents=[], fetched_at=datetime.now(timezone.utc),
        )

    async def process_webhook(self, payload: dict) -> list[RawIncident]:
        """Process an incoming WhatsApp webhook payload."""
        incidents = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                messages = change.get("value", {}).get("messages", [])
                for msg in messages:
                    if msg.get("type") == "text":
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=msg,
                            source_id=msg.get("id"),
                            caller_phone=msg.get("from"),
                            description=msg.get("text", {}).get("body"),
                            timestamp=datetime.fromisoformat(msg["timestamp"]) if "timestamp" in msg else None,
                        ))
                    elif msg.get("type") == "location":
                        loc = msg.get("location", {})
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=msg,
                            source_id=msg.get("id"),
                            caller_phone=msg.get("from"),
                            latitude=float.0(loc.get("latitude", 0)),
                            longitude=float(loc.get("longitude", 0)),
                            location_text=loc.get("name") or loc.get("address"),
                            timestamp=datetime.fromisoformat(msg["timestamp"]) if "timestamp" in msg else None,
                        ))
                    elif msg.get("type") == "image":
                        incidents.append(RawIncident(
                            channel_id=self.channel_id,
                            raw_data=msg,
                            source_id=msg.get("id"),
                            caller_phone=msg.get("from"),
                            media_urls=[msg.get("image", {}).get("id", "")],
                            timestamp=datetime.fromisoformat(msg["timestamp"]) if "timestamp" in msg else None,
                        ))
        return incidents

    async def normalize(self, raw: RawIncident) -> dict:
        return {
            "channel": "whatsapp_business",
            "reporter_phone": raw.caller_phone,
            "hazard_type": "other",  # AI will classify
            "severity": "medium",
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "reverse_geocode": raw.location_text,
            "summary_text": raw.description,
            "media_urls": raw.media_urls,
            "needs_swarm": False,
        }

    async def send_alert(self, incident_id: str, message: str) -> bool:
        """Send WhatsApp message back to reporter."""
        # Implementation uses WhatsApp Cloud API
        return False
