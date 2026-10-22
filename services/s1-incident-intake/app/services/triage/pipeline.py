"""
S1 → S9 → S2 Pipeline Integration
===================================

When S1 creates an incident:
  1. Call S9 AI triage → get severity + swarm recommendation
  2. Publish incidents.ai_triaged to Kafka
  3. Push to S2 review queue for Duty Officer approval

This module is called by the S1 orchestrator after fetching incidents.
"""

import httpx
import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("s1.triage_pipeline")

# Import S9 triage engine directly (same process in dev, separate in prod)
from ai_ml.pipelines.triage.engine import triage_engine


async def run_triage_and_queue(incident: dict, kafka_producer=None) -> dict:
    """
    Full pipeline: AI triage → Kafka → S2 review queue.

    This is the critical path:
      1. AI classifies severity and recommends swarm config
      2. Results go to S2 for human review (ALWAYS)
      3. No dispatch happens without Duty Officer approval
    """
    # Step 1: Run AI triage
    try:
        triage_result = await triage_engine.triage(incident)
    except Exception as e:
        logger.error(f"Triage failed for incident {incident.get('incident_id')}: {e}")
        triage_result = {
            "ai_severity_prediction": "medium",
            "ai_confidence_score": 0.0,
            "needs_swarm": False,
            "model_version": "fallback",
        }

    # Step 2: Merge triage results into incident
    incident.update({
        "status": "ai_triaged",
        "severity": triage_result.get("ai_severity_prediction", "medium"),
        "ai_confidence_score": triage_result.get("ai_confidence_score", 0.0),
        "ai_severity_prediction": triage_result.get("ai_severity_prediction"),
        "needs_swarm": triage_result.get("needs_swarm", False),
        "ai_swarm_recommendation": triage_result.get("ai_swarm_recommendation"),
        "needs_human_team": triage_result.get("needs_human_team", False),
        "human_team_requests": triage_result.get("human_team_requests", []),
        "triaged_at": triage_result.get("triaged_at"),
    })

    # Step 3: Publish incidents.ai_triaged to Kafka
    if kafka_producer:
        await kafka_producer.send_incident_triaged(
            incident.get("incident_id", ""), triage_result
        )

    # Step 4: Push to S2 review queue
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "http://s2-review-dashboard:8002/api/v1/review/incoming",
                json=incident,
            )
            if resp.status_code == 200:
                logger.info(f"Incident {incident.get('incident_id')} queued for review in S2")
            else:
                logger.warning(f"S2 queue push failed: {resp.status_code}")
    except Exception as e:
        # S2 might not be running in dev — that's OK
        logger.debug(f"S2 not reachable: {e}")

    return incident
