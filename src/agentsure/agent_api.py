from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .agents.serviceops import ServiceOpsAgent
from .db import SessionLocal
from .models import ApprovalRecord, AuditEvent


router = APIRouter(prefix="/v1")


# ============================================================
# Database dependency
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# ServiceOps Agent API
# ============================================================

class ServiceOpsRequest(BaseModel):
    incident_id: str = Field(
        min_length=1,
        max_length=128,
    )
    user_message: str = Field(
        min_length=1,
        max_length=10000,
    )


@router.post("/agents/serviceops/run")
def run_serviceops_agent(
    request: ServiceOpsRequest,
    db: Session = Depends(get_db),
):
    agent = ServiceOpsAgent()

    return agent.run(
        db,
        request.incident_id,
        request.user_message,
    )


# ============================================================
# Approval API
# ============================================================

class ApprovalDecisionRequest(BaseModel):
    decided_by: str = Field(
        min_length=1,
        max_length=128,
    )
    reason: str | None = Field(
        default=None,
        max_length=1000,
    )


def _serialize_approval(
    approval: ApprovalRecord,
) -> dict:
    return {
        "approval_id": approval.approval_id,
        "run_id": approval.run_id,
        "agent_id": approval.agent_id,
        "incident_id": approval.incident_id,
        "actor": approval.actor,
        "action": approval.action,
        "risk_level": approval.risk_level,
        "target": approval.target,
        "normalized_parameters": approval.normalized_parameters,
        "policy_version": approval.policy_version,
        "status": approval.status,
        "requested_at": approval.requested_at,
        "expires_at": approval.expires_at,
        "decided_at": approval.decided_at,
        "decided_by": approval.decided_by,
        "decision_reason": approval.decision_reason,
    }


def _get_approval(
    approval_id: str,
    db: Session,
) -> ApprovalRecord:
    approval = db.get(
        ApprovalRecord,
        approval_id,
    )

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Approval not found",
        )

    return approval


def _check_pending_and_not_expired(
    approval: ApprovalRecord,
    db: Session,
) -> None:
    now = datetime.now(timezone.utc)

    if approval.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Approval is already resolved: "
                f"{approval.status}"
            ),
        )

    expires_at = approval.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if now >= expires_at:
        approval.status = "EXPIRED"

        db.commit()
        db.refresh(approval)

        raise HTTPException(
            status_code=409,
            detail="Approval has expired",
        )


@router.get("/approvals/{approval_id}")
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
):
    approval = _get_approval(
        approval_id,
        db,
    )

    return _serialize_approval(approval)


@router.post("/approvals/{approval_id}/approve")
def approve_request(
    approval_id: str,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    approval = _get_approval(
        approval_id,
        db,
    )

    _check_pending_and_not_expired(
        approval,
        db,
    )

    now = datetime.now(timezone.utc)

    approval.status = "APPROVED"
    approval.decided_at = now
    approval.decided_by = request.decided_by
    approval.decision_reason = request.reason

    db.add(
        AuditEvent(
            run_id=approval.run_id,
            event_type="approval.approved",
            payload={
                "approval_id": approval.approval_id,
                "agent_id": approval.agent_id,
                "incident_id": approval.incident_id,
                "action": approval.action,
                "risk_level": approval.risk_level,
                "decided_by": request.decided_by,
                "reason": request.reason,
                "target": approval.target,
                "normalized_parameters": (
                    approval.normalized_parameters
                ),
                "policy_version": (
                    approval.policy_version
                ),
            },
        )
    )

    db.commit()
    db.refresh(approval)

    return _serialize_approval(approval)


@router.post("/approvals/{approval_id}/reject")
def reject_request(
    approval_id: str,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    approval = _get_approval(
        approval_id,
        db,
    )

    _check_pending_and_not_expired(
        approval,
        db,
    )

    now = datetime.now(timezone.utc)

    approval.status = "REJECTED"
    approval.decided_at = now
    approval.decided_by = request.decided_by
    approval.decision_reason = request.reason

    db.add(
        AuditEvent(
            run_id=approval.run_id,
            event_type="approval.rejected",
            payload={
                "approval_id": approval.approval_id,
                "agent_id": approval.agent_id,
                "incident_id": approval.incident_id,
                "action": approval.action,
                "risk_level": approval.risk_level,
                "decided_by": request.decided_by,
                "reason": request.reason,
                "target": approval.target,
                "normalized_parameters": (
                    approval.normalized_parameters
                ),
                "policy_version": (
                    approval.policy_version
                ),
            },
        )
    )

    db.commit()
    db.refresh(approval)

    return _serialize_approval(approval)