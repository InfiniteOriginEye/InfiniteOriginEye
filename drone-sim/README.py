"""
Drone Simulation Layer
======================

Since actual drone hardware is not available, we simulate:
  - Mother Drone: 3D mapping, sensor streams, high-altitude relay
  - Legion Commanders: Ant (search), Bee (relay), Medical (delivery)
  - Individual Drones: Telemetry, battery, health status

Communication: MQTT 5.0 (EMQX broker) - same protocol as real drones
  Topic structure:
    drone/{drone_id}/telemetry     - Position, speed, battery, health
    drone/{drone_id}/command       - Goto, hover, return-to-base, payload-drop
    drone/{drone_id}/video         - H.264 stream (simulated with static frames)
    drone/{drone_id}/sensor        - Simulated sensor data (thermal, lidar)
    swarm/{mission_id}/status      - Overall swarm status
    swarm/{mission_id}/formation   - Formation updates

MAVLink: Simulated via SITL (Software In The Loop) if needed
"""
