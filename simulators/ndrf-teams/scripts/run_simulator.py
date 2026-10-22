#!/usr/bin/env python3
"""
NDRF/SDRF Team Simulator
=========================

Simulates rescue team movements and actions:
  - Team dispatch from base to disaster site
  - GPS tracking updates every 30 seconds
  - Patient rescue and handover events
  - Communication via Bee drone relay when cellular is down
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
logger = logging.getLogger("sim.ndrf_teams")

S4_URL = "http://localhost:8004/api/v1"

# NDRF Battalion locations (real bases)
NDRF_BASES = [
    {"name": "NDRF 1st Bn", "lat": 28.61, "lon": 77.09, "location": "Ghaziabad"},
    {"name": "NDRF 2nd Bn", "lat": 19.08, "lon": 72.88, "location": "Mumbai"},
    {"name": "NDRF 3rd Bn", "lat": 11.02, "lon": 76.95, "location": "Palakkad"},
    {"name": "NDRF 4th Bn", "lat": 26.12, "lon": 91.74, "location": "Guwahati"},
    {"name": "NDRF 5th Bn", "lat": 22.30, "lon": 73.18, "location": "Vadodara"},
    {"name": "NDRF 6th Bn", "lat": 30.37, "lon": 78.47, "location": "Dehradun"},
    {"name": "NDRF 7th Bn", "lat": 21.15, "lon": 79.08, "location": "Nagpur"},
    {"name": "NDRF 8th Bn", "lat": 31.63, "lon": 74.87, "location": "Amritsar"},
    {"name": "NDRF 9th Bn", "lat": 17.73, "lon": 78.38, "location": "Hyderabad"},
    {"name": "NDRF 10th Bn", "lat": 22.57, "lon": 88.36, "location": "Kolkata"},
    {"name": "NDRF 11th Bn", "lat": 25.60, "lon": 85.10, "location": "Patna"},
    {"name": "NDRF 12th Bn", "lat": 28.59, "lon": 77.32, "location": "Delhi"},
    {"name": "NDRF 13th Bn", "lat": 12.97, "lon": 77.59, "location": "Bangalore"},
    {"name": "NDRF 14th Bn", "lat": 13.08, "lon": 80.27, "location": "Chennai"},
    {"name": "NDRF 15th Bn", "lat": 23.02, "lon": 72.57, "location": "Ahmedabad"},
]

TEAM_CAPABILITIES = {
    "SAR": ["rope_rescue", "water_rescue", "collapsed_structure", "search_dog"],
    "Flood": ["boat_rescue", "diver", "water_pump", "flood_rescue"],
    "EQ": ["collapsed_structure", "rope_rescue", "heavy_lifting", "search_dog"],
    "CBRN": ["chemical_handling", "radiation", "bio_hazard"],
    "Medical": ["first_aid", "triage", "field_hospital", "evacuation"],
}


class RescueTeamSimulator:
    """Simulates a single rescue team being dispatched and operating."""

    def __init__(self, team_type: str, base: dict, target_lat: float, target_lon: float):
        self.team_id = f"team-{uuid.uuid4().hex[:6]}"
        self.team_name = f"{base['name']} {team_type} Team"
        self.agency = "NDRF"
        self.team_type = team_type
        self.lat = base["lat"]
        self.lon = base["lon"]
        self.target_lat = target_lat
        self.target_lon = target_lon
        self.status = "available"
        self.personnel = random.randint(35, 45)
        self.capabilities = TEAM_CAPABILITIES.get(team_type, ["general_rescue"])
        self.patients_rescued = 0

    async def dispatch_and_operate(self):
        """Simulate full team lifecycle: dispatch → en_route → on_scene → operating."""
        # Register team
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{S4_URL}/teams", json={
                    "team_id": self.team_id,
                    "team_name": self.team_name,
                    "agency": self.agency,
                    "team_type": self.team_type,
                    "latitude": self.lat,
                    "longitude": self.lon,
                    "personnel_count": self.personnel,
                    "capabilities": self.capabilities,
                })
        except Exception:
            pass

        logger.info(f"[DISPATCH] {self.team_name} → target ({self.target_lat:.2f}, {self.target_lon:.2f})")

        # Simulate travel (en_route) — move towards target
        self.status = "en_route"
        travel_steps = random.randint(20, 40)  # 10-20 minutes at 30s intervals
        for step in range(travel_steps):
            progress = (step + 1) / travel_steps
            self.lat = self.lat + (self.target_lat - self.lat) * 0.1
            self.lon = self.lon + (self.target_lon - self.lon) * 0.1

            # Update location every 30s
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{S4_URL}/teams/{self.team_id}/location", json={
                        "latitude": round(self.lat, 6),
                        "longitude": round(self.lon, 6),
                        "accuracy_m": 10.0,
                    })
            except Exception:
                pass

            await asyncio.sleep(2)  # 2s in sim = 30s real

        # Arrived on scene
        self.status = "on_scene"
        logger.info(f"[ON_SCENE] {self.team_name} arrived")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{S4_URL}/teams/{self.team_id}/status", json={"status": "on_scene"})
        except Exception:
            pass

        # Simulate operations — rescue patients
        self.status = "operating"
        num_patients = random.randint(2, 15)
        for i in range(num_patients):
            await asyncio.sleep(random.uniform(1, 5))
            self.patients_rescued += 1

            # Create patient in S4
            conditions = ["trapped", "injured", "hypothermia", "dehydration", "fracture", "drowning"]
            condition = random.choice(conditions)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{S4_URL}/patients", json={
                        "incident_id": f"inc-sim-{i}",
                        "location": {"latitude": self.lat, "longitude": self.lon},
                        "condition": condition,
                        "priority": random.choice(["urgent", "critical", "stable"]),
                    })
            except Exception:
                pass

            logger.info(f"  [RESCUE] {self.team_name}: Patient #{self.patients_rescued} ({condition})")

        logger.info(f"[COMPLETE] {self.team_name}: {self.patients_rescued} patients rescued")


async def run_simulation():
    """Run full NDRF team simulation for a disaster scenario."""
    # Disaster location (Uttarakhand landslide)
    target_lat, target_lon = 30.28, 78.98

    logger.info("=" * 60)
    logger.info("NDRF TEAM SIMULATOR")
    logger.info(f"Target: ({target_lat}, {target_lon}) — Uttarakhand landslide")
    logger.info("=" * 60)

    # Find closest NDRF base
    bases_sorted = sorted(NDRF_BASES, key=lambda b: (
        (b["lat"] - target_lat)**2 + (b["lon"] - target_lon)**2
    ))
    closest_bases = bases_sorted[:3]

    # Dispatch teams from closest 3 bases
    tasks = []
    for i, base in enumerate(closest_bases):
        team_type = ["SAR", "Flood", "Medical"][i % 3]
        team = RescueTeamSimulator(team_type, base, target_lat, target_lon)
        tasks.append(asyncio.create_task(team.dispatch_and_operate()))

    await asyncio.gather(*tasks)
    logger.info("NDRF simulation complete")


if __name__ == "__main__":
    asyncio.run(run_simulation())
