#!/usr/bin/env python3
"""
ERSS/112 Simulator - Generates realistic Indian disaster incidents
=================================================================

Since we don't have real ERSS API access, this simulator generates
incidents that mimic what ERSS/112 PSAP operators would enter.

Runs as a cron job or continuous loop, pushing to S1 via API.

Scenarios based on real disaster patterns in pilot states.
"""

import asyncio
import json
import random
import uuid
import sys
import logging
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sim.erss")

S1_URL = "http://localhost:8001/api/v1/incidents"

# Realistic disaster scenarios for each pilot state
STATE_SCENARIOS = {
    "Uttarakhand": [
        {
            "district": "Rudraprayag", "lat": 30.28, "lon": 78.98,
            "hazard": "landslide", "severity": "critical",
            "desc": "Major landslide on Rishikesh-Badrinath NH-58, 50+ vehicles stranded. Rain continues. Need immediate rescue.",
        },
        {
            "district": "Chamoli", "lat": 30.41, "lon": 79.51,
            "hazard": "cloudburst", "severity": "critical",
            "desc": "Cloudburst causing flash flood in Raini village area. Multiple houses swept away. People trapped on rooftops.",
        },
        {
            "district": "Uttarkashi", "lat": 30.73, "lon": 78.44,
            "hazard": "earthquake", "severity": "high",
            "desc": "Earthquake tremors (M4.5) felt. Cracks in buildings reported in town. People in panic.",
        },
        {
            "district": "Pauri Garhwal", "lat": 29.85, "lon": 78.78,
            "hazard": "landslide", "severity": "high",
            "desc": "Landslide blocking road to Pauri. 15 people stranded on bus. Needs rope rescue.",
        },
        {
            "district": "Dehradun", "lat": 30.32, "lon": 78.03,
            "hazard": "flood", "severity": "medium",
            "desc": "Song river overflowing in Rajpur area. Low-lying houses flooded. Evacuation may be needed.",
        },
    ],
    "Kerala": [
        {
            "district": "Wayanad", "lat": 11.59, "lon": 76.08,
            "hazard": "landslide", "severity": "critical",
            "desc": "Massive landslide in Meppadi-Punchiri area. Tea estate workers trapped. 100+ feared buried. Urgent rescue needed.",
        },
        {
            "district": "Alappuzha", "lat": 9.50, "lon": 76.33,
            "hazard": "flood", "severity": "high",
            "desc": "Kuttanad region severely flooded. Pamba river 1.5m above danger level. Thousands marooned. Boat rescue needed.",
        },
        {
            "district": "Idukki", "lat": 9.85, "lon": 76.97,
            "hazard": "landslide", "severity": "high",
            "desc": "Landslide in Munnar area blocking road. Tourists stranded in resort. Access cut off.",
        },
        {
            "district": "Ernakulam", "lat": 9.98, "lon": 76.30,
            "hazard": "flood", "severity": "medium",
            "desc": "Heavy waterlogging in Kochi low-lying areas. Traffic paralyzed. Minor flooding in homes.",
        },
    ],
    "Tamil Nadu": [
        {
            "district": "Chennai", "lat": 13.08, "lon": 80.27,
            "hazard": "flood", "severity": "high",
            "desc": "Heavy waterlogging in Velachery, Tambaram. Adyar river rising. 500+ families in relief camps.",
        },
        {
            "district": "Cuddalore", "lat": 11.75, "lon": 79.77,
            "hazard": "cyclone", "severity": "critical",
            "desc": "Cyclone approaching Cuddalore coast. Wind speed 120 kph. Fishing boats at sea. Mass evacuation ordered.",
        },
        {
            "district": "Nagapattinam", "lat": 10.77, "lon": 79.84,
            "hazard": "flood", "severity": "high",
            "desc": "Coastal flooding from storm surge. 20 villages affected. Seawater intrusion in farmland.",
        },
    ],
    "Assam": [
        {
            "district": "Darrang", "lat": 26.47, "lon": 92.19,
            "hazard": "flood", "severity": "critical",
            "desc": "Brahmaputra embankment breach at Sipajhar. 30 villages inundated. Thousands marooned on embankments. Urgent boat rescue.",
        },
        {
            "district": "Barpeta", "lat": 26.32, "lon": 91.01,
            "hazard": "flood", "severity": "high",
            "desc": "Brahmaputra above danger level. 15,000 people affected. Relief camps full. Need additional shelters.",
        },
        {
            "district": "Cachar", "lat": 24.82, "lon": 92.80,
            "hazard": "flood", "severity": "high",
            "desc": "Barak river flooding. Silchar town partially submerged. Airport runway under water.",
        },
        {
            "district": "Golaghat", "lat": 26.50, "lon": 93.97,
            "hazard": "flood", "severity": "medium",
            "desc": "Dhansiri river overflowing. Paddy fields submerged. Crops damaged.",
        },
    ],
    "Himachal Pradesh": [
        {
            "district": "Kullu", "lat": 31.96, "lon": 77.11,
            "hazard": "flood", "severity": "high",
            "desc": "Beas river flash flood after cloudburst. Tourists stranded near Manali. 3 vehicles swept away.",
        },
        {
            "district": "Shimla", "lat": 31.10, "lon": 77.17,
            "hazard": "landslide", "severity": "high",
            "desc": "Major landslide on Shimla-Kalka highway. 200m road washed away. Traffic stranded 5km.",
        },
        {
            "district": "Kinnaur", "lat": 31.63, "lon": 78.46,
            "hazard": "landslide", "severity": "critical",
            "desc": "Multiple landslides blocking all roads. 100+ tourists trapped. Need helicopter evacuation.",
        },
        {
            "district": "Mandi", "lat": 31.71, "lon": 76.73,
            "hazard": "flood", "severity": "medium",
            "desc": "Heavy rain causing waterlogging. Local streams overflowing. Minor damage to property.",
        },
    ],
}


async def generate_incident() -> dict:
    """Generate a single realistic ERSS incident."""
    state = random.choice(list(STATE_SCENARIOS.keys()))
    scenario = random.choice(STATE_SCENARIOS[state])

    incident = {
        "incident_id": str(uuid.uuid4()),
        "channel": "erss_112",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
        "reporter_name": f"Caller-{random.randint(1000, 9999)}",
        "reporter_phone": f"+91{random.randint(7000000000, 9999999999)}",
        "contact_consent": True,
        "latitude": scenario["lat"] + random.gauss(0, 0.005),
        "longitude": scenario["lon"] + random.gauss(0, 0.005),
        "state": state,
        "district": scenario["district"],
        "hazard_type": scenario["hazard"],
        "severity": scenario["severity"],
        "summary_text": scenario["desc"],
        "erss_incident_id": f"ERSS-{state[:2].upper()}-{random.randint(100000, 999999)}",
        "landmark": random.choice(["Near bus stand", "Highway", "Village center", "Bridge", "Temple area", ""]) if random.random() > 0.3 else None,
        "estimated_scale": random.choice(["village", "town", "district", "block"]),
    }
    return incident


async def push_to_s1(incident: dict) -> bool:
    """Push generated incident to S1 intake service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(S1_URL, json=incident)
            if resp.status_code in (200, 201):
                logger.info(f"  → Pushed to S1: {incident['erss_incident_id']} ({incident['severity']})")
                return True
            else:
                logger.warning(f"  → S1 returned {resp.status_code}")
                return False
    except Exception as e:
        logger.debug(f"S1 not reachable: {e}")
        return False


async def simulate_loop(interval_s: int = 30, count: int = None):
    """Generate and push incidents in a loop."""
    logger.info(f"ERSS Simulator starting — interval: {interval_s}s")
    logger.info(f"Target: {S1_URL}")

    i = 0
    while True:
        i += 1
        incident = await generate_incident()
        logger.info(
            f"[{i}] ERSS/{incident['state']} | {incident['hazard_type']} | "
            f"{incident['severity']} | {incident['district']}"
        )
        await push_to_s1(incident)

        if count and i >= count:
            break

        await asyncio.sleep(interval_s)


if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    max_count = int(sys.argv[2]) if len(sys.argv) > 2 else None
    asyncio.run(simulate_loop(interval, max_count))
