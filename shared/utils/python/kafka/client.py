"""
Shared Kafka Producer/Consumer for SC&C Services
=================================================

All services use this module to:
  - Produce events to Kafka topics
  - Consume events and route to service-specific handlers

Topics (from infra/kafka-topics.yaml):
  incidents.created    → S1 produces, S2 + S9 consume
  incidents.ai_triaged → S9 produces, S2 consumes
  incidents.approved   → S2 produces, S3 + S4 consume
  alerts.early_warning → S5 produces, S1 consumes
  swarm.deploy         → S3 produces
  teams.dispatched     → S4 produces
  audit.events         → All services produce, S7 consumes
"""

import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger("scc.kafka")


class KafkaProducer:
    """
    Async Kafka producer wrapper.

    In production: uses aiokafka.AIOKafkaProducer
    In development: logs events to console (no Kafka dependency)
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092", use_real_kafka: bool = False):
        self.bootstrap_servers = bootstrap_servers
        self.use_real_kafka = use_real_kafka
        self._producer = None

    async def start(self):
        if self.use_real_kafka:
            try:
                from aiokafka import AIOKafkaProducer
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: v if isinstance(v, bytes) else json.dumps(v).encode(),
                    key_serializer=lambda k: k.encode() if isinstance(k, str) else k,
                )
                await self._producer.start()
                logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
            except Exception as e:
                logger.warning(f"Kafka connection failed, falling back to console: {e}")
                self.use_real_kafka = False
        else:
            logger.info("Kafka producer in CONSOLE mode (no broker)")

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def send(self, topic: str, key: str = None, value: dict | bytes = None):
        """Send a message to a Kafka topic."""
        if self.use_real_kafka and self._producer:
            await self._producer.send_and_wait(topic, value=value, key=key)
        else:
            # Console mode — log the event
            val = value if isinstance(value, dict) else json.loads(value) if isinstance(value, bytes) else value
            logger.info(f"[KAFKA] {topic} | key={key} | {json.dumps(val, default=str)[:120]}")

    async def send_incident_created(self, incident: dict):
        """S1: Publish incident.created event."""
        await self.send("incidents.created", key=incident.get("incident_id", ""), value=incident)

    async def send_incident_triaged(self, incident_id: str, triage_result: dict):
        """S9: Publish incident.ai_triaged event."""
        await self.send("incidents.ai_triaged", key=incident_id, value=triage_result)

    async def send_incident_approved(self, incident: dict):
        """S2: Publish incident.approved event (Duty Officer approved)."""
        await self.send("incidents.approved", key=incident.get("incident_id", ""), value=incident)

    async def send_early_warning(self, alert: dict):
        """S5: Publish alerts.early_warning event."""
        await self.send("alerts.early_warning", key=alert.get("alert_id", ""), value=alert)

    async def send_team_dispatched(self, team_id: str, dispatch_data: dict):
        """S4: Publish teams.dispatched event."""
        await self.send("teams.dispatched", key=team_id, value=dispatch_data)

    async def send_audit_event(self, entity_type: str, entity_id: str, action: str, actor_id: str, metadata: dict = None):
        """All: Publish audit.events for S7 compliance."""
        await self.send("audit.events", key=entity_id, value={
            "entity_type": entity_type, "entity_id": entity_id,
            "action": action, "actor_id": actor_id,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


class KafkaConsumer:
    """
    Async Kafka consumer wrapper.

    Subscribes to topics and calls handler functions for each message.
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092", group_id: str = "scc",
                 use_real_kafka: bool = False):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.use_real_kafka = use_real_kafka
        self._consumer = None
        self.handlers: dict[str, Callable] = {}

    def register_handler(self, topic: str, handler: Callable):
        """Register a handler function for a topic."""
        self.handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")

    async def start(self):
        if not self.handlers:
            logger.warning("No handlers registered, consumer not starting")
            return

        if self.use_real_kafka:
            try:
                from aiokafka import AIOKafkaConsumer
                self._consumer = AIOKafkaConsumer(
                    *self.handlers.keys(),
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode()),
                    key_deserializer=lambda m: m.decode() if m else None,
                )
                await self._consumer.start()
                logger.info(f"Kafka consumer started — topics: {list(self.handlers.keys())}")

                async for msg in self._consumer:
                    handler = self.handlers.get(msg.topic)
                    if handler:
                        try:
                            await handler(msg.key, msg.value)
                        except Exception as e:
                            logger.error(f"Handler error for {msg.topic}: {e}")
            except Exception as e:
                logger.warning(f"Kafka consumer failed: {e}")
                self.use_real_kafka = False
        else:
            logger.info(f"Kafka consumer in CONSOLE mode — topics: {list(self.handlers.keys())}")

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()
