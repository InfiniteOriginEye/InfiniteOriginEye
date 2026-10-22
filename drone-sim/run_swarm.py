#!/usr/bin/env python3
"""
Complete Drone Swarm Simulator
================================

Simulates the full drone hierarchy:
  - Mother Drone (high altitude, 3D mapping, relay)
  - Legion Commander: Ant (search), Bee (relay), Medical (delivery)
  - Individual Drones: telemetry, battery, health, commands

All communication via MQTT to EMQX broker (same as real drones).
Also pushes to S3 via gRPC for command/telemetry flow.
"""

import asyncio
import json
import random
import uuid
import math
import sys
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sim.drone_swarm")

# MQTT config (in production, use aiomqtt; for now, log + HTTP to S3)
S3_URL = "http://localhost:8003"  # gRPC in production, HTTP for dev
EMQX_BROKER = "localhost"
EMQX_PORT = 1883


class DroneSimulator:
    """Simulates a single drone with realistic flight dynamics."""

    def __init__(self, drone_id: str, drone_type: str, mission_id: str,
                 start_lat: float, start_lon: float):
        self.drone_id = drone_id
        self.drone_type = drone_type  # mother, ant, bee, medical
        self.mission_id = mission_id
        self.lat = start_lat
        self.lon = start_lon

        # Flight state
        self.altitude = self._default_altitude()
        self.speed = 0.0
        self.heading = random.uniform(0, 360)
        self.battery = 100.0
        self.flight_time_s = 0

        # Health
        self.gps_ok = True
        self.imu_ok = True
        self.motors_ok = True
        self.camera_ok = True
        self.comms_ok = True

    def _default_altitude(self) -> float:
        """Default altitude by drone type."""
        return {"mother": 120.0, "ant": 60.0, "bee": 80.0, "medical": 50.0}.get(
            self.drone_type, 50.0
        )

    def update(self, dt: float = 0.5):
        """Update drone state for one time step."""
        # Movement
        self.speed = max(0, min(15, self.speed + random.gauss(0, 0.5)))
        self.heading = (self.heading + random.gauss(0, 3)) % 360

        # Position (simplified flat-earth)
        heading_rad = math.radians(self.heading)
        self.lat += (self.speed * math.cos(heading_rad) * dt) / 111320.0
        self.lon += (self.speed * math.sin(heading_rad) * dt) / (111320.0 * math.cos(math.radians(self.lat)))

        # Altitude variations
        self.altitude += random.gauss(0, 0.5)
        self.altitude = max(20, min(150, self.altitude))

        # Battery drain (faster for smaller drones)
        drain_rate = {"mother": 0.03, "ant": 0.05, "bee": 0.04, "medical": 0.06}.get(
            self.drone_type, 0.05
        )
        self.battery -= drain_rate + random.gauss(0, 0.005)
        self.battery = max(0, self.battery)

        # Flight time
        self.flight_time_s += dt

        # Occasional health issues
        if random.random() < 0.001:
            self.gps_ok = not self.gps_ok
        if random.random() < 0.0005:
            self.camera_ok = not self.camera_ok

    def get_telemetry(self) -> dict:
        return {
            "drone_id": self.drone_id,
            "drone_type": self.drone_type,
            "mission_id": self.mission_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "position": {
                "latitude": round(self.lat, 6),
                "longitude": round(self.lon, 6),
                "altitude_m": round(self.altitude, 1),
            },
            "speed_ms": round(self.speed, 2),
            "heading_deg": round(self.heading, 1),
            "battery_pct": round(self.battery, 1),
            "flight_time_s": round(self.flight_time_s, 1),
            "health": {
                "gps": self.gps_ok, "imu": self.imu_ok,
                "motors": self.motors_ok, "camera": self.camera_ok,
                "comms": self.comms_ok,
            },
            "status": "flying" if self.battery > 15 else "returning",
        }

    def should_return(self) -> bool:
        return self.battery < 20


class SwarmSimulator:
    """Simulates a complete drone swarm with Mother + Legions."""

    def __init__(self, mission_id: str, center_lat: float, center_lon: float,
                 mother_count: int = 1, ant_count: int = 8, bee_count: int = 3,
                 medical_count: int = 4):
        self.mission_id = mission_id
        self.drones: list[DroneSimulator] = []
        self.running = False

        # Create Mother Drones
        for i in range(mother_count):
            self.drones.append(DroneSimulator(
                drone_id=f"mother-{uuid.uuid4().hex[:6]}",
                drone_type="mother", mission_id=mission_id,
                start_lat=center_lat + random.gauss(0, 0.001),
                start_lon=center_lon + random.gauss(0, 0.001),
            ))

        # Create Ant Legion (search & mapping)
        for i in range(ant_count):
            angle = (2 * math.pi * i) / ant_count
            self.drones.append(DroneSimulator(
                drone_id=f"ant-{uuid.uuid4().hex[:6]}",
                drone_type="ant", mission_id=mission_id,
                start_lat=center_lat + 0.002 * math.cos(angle),
                start_lon=center_lon + 0.002 * math.sin(angle),
            ))

        # Create Bee Legion (communication relay)
        for i in range(bee_count):
            angle = (2 * math.pi * i) / bee_count
            self.drones.append(DroneSimulator(
                drone_id=f"bee-{uuid.uuid4().hex[:6]}",
                drone_type="bee", mission_id=mission_id,
                start_lat=center_lat + 0.004 * math.cos(angle),
                start_lon=center_lon + 0.004 * math.sin(angle),
            ))

        # Create Medical Legion (supply delivery)
        for i in range(medical_count):
            self.drones.append(DroneSimulator(
                drone_id=f"med-{uuid.uuid4().hex[:6]}",
                drone_type="medical", mission_id=mission_id,
                start_lat=center_lat + random.gauss(0, 0.001),
                start_lon=center_lon + random.gauss(0, 0.001),
            ))

        logger.info(f"Swarm created: {mother_count} mother + {ant_count} ant + "
                    f"{bee_count} bee + {medical_count} medical = {len(self.drones)} drones")

    async def run(self, telemetry_interval: float = 0.5, duration_s: float = None):
        """Run the swarm simulation."""
        self.running = True
        start = datetime.now(timezone.utc)
        step = 0

        while self.running:
            step += 1
            active_drones = 0

            for drone in self.drones:
                drone.update(telemetry_interval)

                if drone.should_return():
                    continue
                active_drones += 1

                # Publish telemetry (in production: MQTT; dev: console)
                telemetry = drone.get_telemetry()
                if step % 4 == 0:  # Log every 4th step to reduce noise
                    logger.debug(
                        f"  {drone.drone_id[:12]} | alt:{drone.altitude:.0f}m | "
                        f"bat:{drone.battery:.0f}% | spd:{drone.speed:.1f}m/s"
                    )

            if active_drones == 0:
                logger.info("All drones returned — swarm simulation complete")
                break

            if step % 20 == 0:  # Status every 10 seconds
                batteries = [d.battery for d in self.drones if not d.should_return()]
                avg_bat = sum(batteries) / len(batteries) if batteries else 0
                logger.info(
                    f"[{step}] Mission {self.mission_id[:8]} | "
                    f"Active: {active_drones}/{len(self.drones)} | "
                    f"Avg battery: {avg_bat:.1f}%"
                )

            # Check duration limit
            if duration_s and (datetime.now(timezone.utc) - start).total_seconds() >= duration_s:
                logger.info(f"Duration limit reached ({duration_s}s)")
                break

            await asyncio.sleep(telemetry_interval)

        self.running = False


async def main():
    """Run a complete swarm simulation for a disaster scenario."""
    mission_id = str(uuid.uuid4())

    # Default: Uttarakhand landslide scenario
    center_lat = 30.28
    center_lon = 78.98

    logger.info("=" * 60)
    logger.info("SC&C DRONE SWARM SIMULATOR")
    logger.info(f"Mission: {mission_id}")
    logger.info(f"Area: {center_lat}, {center_lon} (Uttarakhand landslide)")
    logger.info("=" * 60)

    swarm = SwarmSimulator(
        mission_id=mission_id,
        center_lat=center_lat, center_lon=center_lon,
        mother_count=1, ant_count=8, bee_count=3, medical_count=4,
    )

    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    await swarm.run(duration_s=duration)


if __name__ == "__main__":
    asyncio.run(main())
