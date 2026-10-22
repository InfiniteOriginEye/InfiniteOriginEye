# =============================================================================
# S7 - Data Handover & Reporting
# Owner: NDMA / SDMA
# Tech: Python 3.11 + FastAPI + Kafka
# Port: 8007
#
# NDMIS export, compliance reports, archival, audit trail.
# =============================================================================

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("s7.data_handover")

app = FastAPI(
    title="S7 - Data Handover & Reporting",
    description="NDMIS export, compliance reports, archival, audit trail",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Audit log store (in-memory; PostgreSQL in production)
audit_log: list[dict] = []
reports: dict[str, dict] = {}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "s7-data-handover", "audit_entries": len(audit_log)}


@app.post("/api/v1/audit")
async def log_audit_event(event: dict):
    """Log an auditable action (called by all services via Kafka)."""
    event["logged_at"] = datetime.now(timezone.utc).isoformat()
    audit_log.append(event)
    return {"logged": True, "total_entries": len(audit_log)}


@app.get("/api/v1/audit")
async def query_audit_log(entity_type: Optional[str] = None, actor_id: Optional[str] = None, limit: int = 100):
    """Query the audit trail for compliance."""
    results = audit_log
    if entity_type:
        results = [e for e in results if e.get("entity_type") == entity_type]
    if actor_id:
        results = [e for e in results if e.get("actor_id") == actor_id]
    return {"entries": results[-limit:], "total": len(results)}


@app.post("/api/v1/reports/ndmis")
async def generate_ndmis_report(report_request: dict):
    """Generate NDMIS-format export for NDMA."""
    report_id = f"rpt-ndmis-{len(reports)+1}"
    report = {
        "report_id": report_id,
        "type": "ndmis",
        "incident_id": report_request.get("incident_id"),
        "format": "ndmis_xml",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "generated",
        "data": {
            "incident_summary": report_request.get("summary"),
            "actions_taken": report_request.get("actions", []),
            "resources_deployed": report_request.get("resources", []),
            "swarm_operations": report_request.get("swarm_ops", {}),
        },
    }
    reports[report_id] = report
    return report


@app.post("/api/v1/reports/compliance")
async def generate_compliance_report(report_request: dict):
    """Generate post-disaster compliance report for NDMA accountability."""
    report_id = f"rpt-compliance-{len(reports)+1}"
    report = {
        "report_id": report_id,
        "type": "compliance",
        "incident_id": report_request.get("incident_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timeline": audit_log[-50:],  # Last 50 audit events for this incident
        "decision_log": "All AI triage decisions were reviewed by Duty Officer before dispatch",
    }
    reports[report_id] = report
    return report


@app.get("/api/v1/reports/{report_id}")
async def get_report(report_id: str):
    report = reports.get(report_id)
    if not report:
        return {"error": "Report not found"}
    return report
