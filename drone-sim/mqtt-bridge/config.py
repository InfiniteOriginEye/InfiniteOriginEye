"""
MQTT Topic Structure for Drone Communication
=============================================

Broker: EMQX 5.0 (MQTT 5.0)

Topic Hierarchy:
  scc/drone/{drone_id}/telemetry      - Position, speed, battery, health (QoS 1, 2Hz)
  scc/drone/{drone_id}/command        - Commands: goto, hover, rtb, drop (QoS 2)
  scc/drone/{drone_id}/command/ack    - Command acknowledgment (QoS 1)
  scc/drone/{drone_id}/status         - Mode change, health alert (QoS 1)
  scc/drone/{drone_id}/video/config   - Video stream config (WebRTC signaling)
  scc/drone/{drone_id}/sensor/thermal - Thermal camera data
  scc/drone/{drone_id}/sensor/lidar   - LiDAR point cloud chunks

  scc/swarm/{mission_id}/deploy       - Deploy command from S3 (QoS 2)
  scc/swarm/{mission_id}/formation    - Formation update (QoS 1)
  scc/swarm/{mission_id}/recall       - Recall command (QoS 2)
  scc/swarm/{mission_id}/status       - Swarm aggregate status (QoS 1)

  scc/mother/{drone_id}/map           - 3D map data (point cloud, orthophoto)
  scc/mother/{drone_id}/map/config    - Map generation config (resolution, overlap)

MQTT 5.0 Features Used:
  - Shared subscriptions for load-balanced consumers
  - Message expiry for stale telemetry (5 seconds)
  - Payload format indicator (UTF-8 / binary)
  - Reason codes for clean disconnect
  - User properties for tracing (correlation_id, mission_id)
"""

# EMQX MQTT Bridge Configuration
# Bridges drone MQTT messages to Kafka for persistence and cross-service consumption
