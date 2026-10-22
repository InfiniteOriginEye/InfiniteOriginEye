#!/usr/bin/env python3
"""
Drone Simulator - Mother Drone
================================
Simulates a Mother Drone that:
  - Publishes telemetry to MQTT every 500ms
  - Generates simulated 3D map data
  - Commands legion commanders
  - Streams high-altitude video (WebRTC)

MQTT Topics Published:
  scc/drone/{drone_id}/telemetry
  scc/mother/{drone_id}/map
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timezone

import aiomqtt


class MotherDroneSim:
    def __init__(self, drone_id: str, mission_id: str, broker: str = "localhost"):
        self.drone_id = drone_id
        self.mission_id = mission_id
        self.broker = broker
        self.running = False

        # Simulated state
        self.lat = 30.3165  # Default: Uttarakhand
        self.lon = 78.0320
        self.alt = 100.0   # Mother drone altitude (meters AGL)
        self.battery = 100.0
        self.speed = 0.0
        self.heading = 0.0

    async def start(self):
        """Start the Mother Drone simulation."""
        self.running = True
        async with aiomqtt.Client(self.broker) as client:
            print(f"Mother Drone {self.drone_id} connected to MQTT broker")
            while self.running and self.battery > 10:
                # Update simulated position
                self._update_state()

                # Publish telemetry
                telemetry = {
                    "drone_id": self.drone_id,
                    "drone_type": "mother",
                    "mission_id": self.mission_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "position": {
                        "latitude": self.lat,
                        "longitude": self.lon,
                        "altitude_m": self.alt,
                    },
                    "speed_ms": self.speed,
                    "heading_deg": self.heading,
                    "battery_pct": round(self.battery, 1),
                    "health": {
                        "gps": True, "imu": True, "motors": True,
                        "camera": True, "comms": True,
                    },
                }

                topic = f"scc/drone/{self.drone_id}/telemetry"
                await client.publish(topic, json.dumps(telemetry), qos=1)

                await asyncio.sleep(0.5)  # 2 Hz telemetry rate

        print(f"Mother Drone {self.drone_id} simulation ended (battery: {self.battery:.1f}%)")

    def _update_state(self):
        """Simulate flight dynamics."""
        # Random walk for position
        self.lat += random.gauss(0, 0.0001)
        self.lon += random.gauss(0, 0.0001)
        self.heading = (self.heading + random.gauss(0, 5)) % 360
        self.speed = max(0, self.speed + random.gauss(0, 0.5))
        self.battery -= random.uniform(0.01, 0.05)  # Battery drain

    async def stop(self):
        self.running = False


if __name__ == "__main__":
    drone_id = str(uuid.uuid4())
    mission_id = str(uuid.uuid4())
    sim = MotherDroneSim(drone_id, mission_id)
    try:
        asyncio.run(sim.start())
    except KeyboardInterrupt:
        asyncio.run(sim.stop())
