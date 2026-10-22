# =============================================================================
# S2 - Professional Review Dashboard (Backend)
# Owner: SDMA / SEOC
# Tech: Python 3.11 + FastAPI + Kafka
# Port: 8002
#
# SEOC Duty Officer reviews AI-triaged incidents before dispatch.
# Human-in-the-loop: NO swarm/team dispatch happens without Duty Officer approval.
# =============================================================================

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

logger = logging.getLogger("s2.review_dashboard")


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    ESCALATE = "escalate"
    MERGE = "merge"  # Merge with existing incident


# In-memory review queue (replaced with DB + Kafka consumer in production)
review_queue: dict[str, dict] = {}
incident_store: dict[str, dict] = {}


class ReviewOrchestrator:
    """
    Consumes incidents.created + incidents.ai_triaged from Kafka.
    Presents them to Duty Officer for review.
    On approval → publishes incidents.approved → triggers S3/S4 dispatch.
    """

    def __init__(self, kafka_consumer=None, kafka_producer=None):
        self.kafka_consumer = kafka_consumer
        self.kafka_producer = kafka_producer
        self.running = False

    async def add_to_review_queue(self, incident: dict) -> dict:
        """Add an AI-triaged incident to the Duty Officer review queue."""
        incident_id = incident.get("incident_id") or f"inc-{len(review_queue)+1}"
        incident["review_status"] = "pending"
        incident["added_to_queue_at"] = datetime.now(timezone.utc).isoformat()
        review_queue[incident_id] = incident
        incident_store[incident_id] = incident
        logger.info(f"Incident {incident_id} added to review queue — severity: {incident.get('severity')}")
        return {"incident_id": incident_id, "review_status": "pending"}

    async def process_review(
        self, incident_id: str, decision: ReviewDecision,
        reviewer_id: str, override_notes: str = None,
        modified_severity: str = None, modified_hazard: str = None,
        modified_swarm_config: dict = None,
    ) -> dict:
        """
        Process Duty Officer's review decision.

        CRITICAL: This is the human-in-the-loop gate.
        No swarm or team dispatch happens without this approval.
        """
        incident = review_queue.get(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not in review queue")

        incident["review_decision"] = decision.value
        incident["professional_reviewer_id"] = reviewer_id
        incident["review_timestamp"] = datetime.now(timezone.utc).isoformat()
        incident["override_notes"] = override_notes

        if decision == ReviewDecision.APPROVE:
            # Approve AI triage → dispatch swarm + teams
            incident["status"] = "approved"
            review_queue.pop(incident_id, None)

            # Publish incidents.approved → S3 swarm dispatch, S4 team dispatch
            await self._publish_approval(incident)
            logger.info(f"Duty Officer {reviewer_id} APPROVED incident {incident_id} → dispatching")

        elif decision == ReviewDecision.REJECT:
            incident["status"] = "rejected"
            review_queue.pop(incident_id, None)
            logger.info(f"Duty Officer {reviewer_id} REJECTED incident {incident_id}")

        elif decision == ReviewDecision.MODIFY:
            # Duty Officer overrides AI recommendations
            if modified_severity:
                incident["severity"] = modified_severity
            if modified_hazard:
                incident["hazard_type"] = modified_hazard
            if modified_swarm_config:
                incident["swarm_config"] = modified_swarm_config
            incident["status"] = "approved"  # Modified = still approved, just different params
            review_queue.pop(incident_id, None)
            await self._publish_approval(incident)
            logger.info(f"Duty Officer {reviewer_id} MODIFIED + APPROVED incident {incident_id}")

        elif decision == ReviewDecision.ESCALATE:
            # Escalate to SEOC Supervisor or District Collector
            incident["status"] = "escalated"
            logger.info(f"Incident {incident_id} ESCALATED by {reviewer_id}")

        elif decision == ReviewDecision.MERGE:
            incident["status"] = "merged"
            review_queue.pop(incident_id, None)
            logger.info(f"Incident {incident_id} MERGED into existing incident")

        incident_store[incident_id] = incident
        return {"incident_id": incident_id, "status": incident["status"], "decision": decision.value}

    async def _publish_approval(self, incident: dict):
        """Publish approved incident to Kafka for S3/S4 to consume."""
        if self.kafka_producer:
            await self.kafka_producer.send(
                topic="incidents.approved",
                key=incident["incident_id"],
                value=json.dumps(incident).encode(),
            )
        else:
            logger.info(f"[Kafka] incidents.approved → {incident.get('incident_id')}")

        # Also notify S6 ERSS Connector about the dispatch
        if incident.get("erss_incident_id"):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        "http://s6-erss-connector:8006/api/v1/erss/sync",
                        json={
                            "state": incident.get("state"),
                            "incident_id": incident["incident_id"],
                            "status": "dispatching",
                            "swarm_status": "deploying",
                        },
                    )
            except Exception:
                pass

    def get_queue(self, severity_filter: str = None, state_filter: str = None) -> list[dict]:
        """Get pending incidents in the review queue, sorted by severity."""
        queue = list(review_queue.values())
        if severity_filter:
            queue = [i for i in queue if i.get("severity") == severity_filter]
        if state_filter:
            queue = [i for i in queue if i.get("state") == state_filter]
        # Sort: critical first, then high, medium, low
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
        queue.sort(key=lambda i: severity_order.get(i.get("severity"), 5))
        return queue


review_orchestrator = ReviewOrchestrator()

app = FastAPI(
    title="S2 - Professional Review Dashboard",
    description="SEOC Duty Officer review interface — human-in-the-loop approval gate for AI triage decisions",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s2-review-dashboard", "queue_size": len(review_queue)}


@app.get("/api/v1/review/queue")
async def get_review_queue(severity: Optional[str] = None, state: Optional[str] = None):
    """Get all incidents pending Duty Officer review, sorted by severity."""
    return {"queue": review_orchestrator.get_queue(severity, state), "count": len(review_queue)}


@app.get("/api/v1/review/{incident_id}")
async def get_incident_for_review(incident_id: str):
    """Get full details of an incident for the Duty Officer to review."""
    incident = incident_store.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.post("/api/v1/review/{incident_id}/approve")
async def approve_incident(incident_id: str, reviewer_id: str, notes: Optional[str] = None):
    """Duty Officer APPROVES the AI triage decision → triggers swarm + team dispatch."""
    return await review_orchestrator.process_review(
        incident_id, ReviewDecision.APPROVE, reviewer_id, override_notes=notes
    )


@app.post("/api/v1/review/{incident_id}/reject")
async def reject_incident(incident_id: str, reviewer_id: str, reason: str):
    """Duty Officer REJECTS the AI triage — no dispatch."""
    return await review_orchestrator.process_review(
        incident_id, ReviewDecision.REJECT, reviewer_id, override_notes=reason
    )


@app.post("/api/v1/review/{incident_id}/modify")
async def modify_and_approve(
    incident_id: str, reviewer_id: str,
    severity: Optional[str] = None, hazard_type: Optional[str] = None,
    swarm_config: Optional[dict] = None, notes: Optional[str] = None,
):
    """Duty Officer MODIFIES AI recommendations and approves with overrides."""
    return await review_orchestrator.process_review(
        incident_id, ReviewDecision.MODIFY, reviewer_id,
        override_notes=notes, modified_severity=severity,
        modified_hazard=hazard_type, modified_swarm_config=swarm_config,
    )


@app.post("/api/v1/review/{incident_id}/escalate")
async def escalate_incident(incident_id: str, reviewer_id: str, reason: str):
    """Escalate to SEOC Supervisor / District Collector."""
    return await review_orchestrator.process_review(
        incident_id, ReviewDecision.ESCALATE, reviewer_id, override_notes=reason
    )


@app.post("/api/v1/review/{incident_id}/merge")
async def merge_incident(incident_id: str, reviewer_id: str, target_incident_id: str, reason: str):
    """Merge this incident into an existing one (duplicates, same event)."""
    return await review_orchestrator.process_review(
        incident_id, ReviewDecision.MERGE, reviewer_id,
        override_notes=f"Merged into {target_incident_id}: {reason}",
    )


# Kafka consumer endpoint (for S1 to push incidents to review queue)
@app.post("/api/v1/review/incoming")
async def receive_from_s1(incident: dict):
    """Receive AI-triaged incident from S1 (via Kafka or direct API call)."""
    return await review_orchestrator.add_to_review_queue(incident)


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident_status(incident_id: str):
    """Get current status of any incident (approved, rejected, active, etc.)."""
    incident = incident_store.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
