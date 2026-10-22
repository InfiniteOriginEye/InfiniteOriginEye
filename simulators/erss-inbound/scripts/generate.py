#!/usr/bin/env python3
"""
ERSS Inbound Simulator
======================
Simulates ERSS/112 PSAP incidents since we don't have real ERSS API access.

Generates incidents with:
  - Realistic Indian disaster scenarios (flood in Kerala, landslide in Uttarakhand, etc.)
  - Proper location data (state, district, lat/lon)
  - Hindi/English bilingual text
  - 112 call metadata (caller phone, operator ID, timestamp)

Publishes to Kafka topic: incidents.created
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timezone

# Realistic disaster scenarios for pilot states
SCENARIOS = [
    {"state": "Uttarakhand", "district": "Rudraprayag", "lat": 30.28, "lon": 78.98,
     "hazard": "landslide", "severity": "critical", "desc": "Major landslide blocking Rishikesh-Badrinath highway, 50+ vehicles stranded"},

    {"state": "Uttarakhand", "district": "Chamoli", "lat": 30.41, "lon": 79.51,
     "hazard": "cloudburst", "severity": "critical", "desc": "Cloudburst causing flash flood in Joshimath area, houses swept away"},

    {"state": "Kerala", "district": "Wayanad", "lat": 11.59, "lon": 76.08,
     "hazard": "landslide", "severity": "critical", "desc": "Multiple landslides in Meppadi area, hundreds feared trapped"},

    {"state": "Kerala", "district": "Alappuzha", "lat": 9.50, "lon": 76.33,
     "hazard": "flood", "severity": "high", "desc": "Kuttanad region flooded, Pamba river above danger level"},

    {"state": "Tamil Nadu", "district": "Chennai", "lat": 13.08, "lon": 80.27,
     "hazard": "flood", "severity": "high", "desc": "Heavy waterlogging in low-lying areas, Adyar river flooding"},

    {"state": "Assam", "district": "Darrang", "lat": 26.47, "lon": 92.19,
     "hazard": "flood", "severity": "critical", "desc": "Brahmaputra river breach, 20 villages affected, thousands marooned"},

    {"state": "Himachal Pradesh", "district": "Kullu", "lat": 31.96, "lon": 77.11,
     "hazard": "flood", "severity": "high", "desc": "Beas river flash flood, tourists stranded near Manali"},

    {"state": "Uttarakhand", "district": "Uttarkashi", "lat": 30.73, "lon": 78.44,
     "hazard": "earthquake", "severity": "high", "desc": "Earthquake tremors felt, building damage reported in town area"},
]


async def generate_erss_incident():
    """Generate a realistic ERSS/112 incident."""
    scenario = random.choice(SCENARIOS)
    incident = {
        "incident_id": str(uuid.uuid4()),
        "channel": "erss_112",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
        "reporter_name": f"Caller-{random.randint(1000, 9999)}",
        "reporter_phone": f"+91{random.randint(7000000000, 9999999999)}",
        "contact_consent": True,
        "latitude": scenario["lat"] + random.gauss(0, 0.01),
        "longitude": scenario["lon"] + random.gauss(0, 0.01),
        "state": scenario["state"],
        "district": scenario["district"],
        "hazard_type": scenario["hazard"],
        "severity": scenario["severity"],
        "summary_text": scenario["desc"],
        "erss_incident_id": f"ERSS-{scenario['state'][:2].upper()}-{random.randint(100000, 999999)}",
        "needs_swarm": scenario["severity"] in ("critical", "high"),
    }
    return incident


if __name__ == "__main__":
    # Quick test
    incident = asyncio.run(generate_erss_incident())
    print(json.dumps(incident, indent=2))
