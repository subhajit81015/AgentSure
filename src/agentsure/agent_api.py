from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .action_executor import ActionExecutionError
from .agents.serviceops import ServiceOpsAgent
from .authentication import authenticate_actor
from .db import SessionLocal
from .execution_service import ApprovalExecutionService
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


# ============================================================
# Approval serialization
# ============================================================

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


# ============================================================
# Approval lookup
# ============================================================

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


# ============================================================
# Authentication
# ============================================================

def _authenticate_decision_actor(
    decided_by: str,
) -> str:
    """
    Authenticate the human actor responsible for
    approving or rejecting an approval request.

    This is intentionally kept independent from RBAC.
    RBAC can be integrated later without changing
    the existing API contract.
    """

    result = authenticate_actor(decided_by)

    if not result.authenticated:
        raise HTTPException(
            status_code=401,
            detail=result.reason,
        )

    if not result.actor:
        raise HTTPException(
            status_code=401,
            detail="Actor authentication failed.",
        )

    return result.actor


# ============================================================
# Approval state validation
# ============================================================

def _check_pending_and_not_expired(
    approval: ApprovalRecord,
    db: Session,
) -> None:
    now = datetime.now(UTC)

    # --------------------------------------------------------
    # Already resolved
    # --------------------------------------------------------

    if approval.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail=(
                "Approval is already resolved: "
                f"{approval.status}"
            ),
        )

    # --------------------------------------------------------
    # Expiration
    # --------------------------------------------------------

    expires_at = approval.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=UTC,
        )
    else:
        expires_at = expires_at.astimezone(UTC)

    if now >= expires_at:
        approval.status = "EXPIRED"

        db.commit()
        db.refresh(approval)

        raise HTTPException(
            status_code=409,
            detail="Approval has expired",
        )


# ============================================================
# Get Approval
# ============================================================

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


# ============================================================
# Approve Approval
# ============================================================

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

    # --------------------------------------------------------
    # Authenticate decision actor
    # --------------------------------------------------------

    authenticated_actor = _authenticate_decision_actor(
        request.decided_by,
    )

    now = datetime.now(UTC)

    # --------------------------------------------------------
    # Update approval
    # --------------------------------------------------------

    approval.status = "APPROVED"
    approval.decided_at = now
    approval.decided_by = authenticated_actor
    approval.decision_reason = request.reason

    # --------------------------------------------------------
    # Audit event
    # --------------------------------------------------------

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
                "decided_by": authenticated_actor,
                "reason": request.reason,
                "target": approval.target,
                "normalized_parameters": (
                    approval.normalized_parameters
                ),
                "policy_version": (
                    approval.policy_version
                ),
                "authentication": {
                    "authenticated": True,
                    "actor": authenticated_actor,
                },
            },
        )
    )

    db.commit()
    db.refresh(approval)

    return _serialize_approval(approval)


# ============================================================
# Reject Approval
# ============================================================

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

    # --------------------------------------------------------
    # Authenticate decision actor
    # --------------------------------------------------------

    authenticated_actor = _authenticate_decision_actor(
        request.decided_by,
    )

    now = datetime.now(UTC)

    # --------------------------------------------------------
    # Update approval
    # --------------------------------------------------------

    approval.status = "REJECTED"
    approval.decided_at = now
    approval.decided_by = authenticated_actor
    approval.decision_reason = request.reason

    # --------------------------------------------------------
    # Audit event
    # --------------------------------------------------------

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
                "decided_by": authenticated_actor,
                "reason": request.reason,
                "target": approval.target,
                "normalized_parameters": (
                    approval.normalized_parameters
                ),
                "policy_version": (
                    approval.policy_version
                ),
                "authentication": {
                    "authenticated": True,
                    "actor": authenticated_actor,
                },
            },
        )
    )

    db.commit()
    db.refresh(approval)

    return _serialize_approval(approval)


# ============================================================
# Controlled Post-Approval Execution API
# ============================================================

@router.post("/approvals/{approval_id}/execute")
def execute_approved_request(
    approval_id: str,
    db: Session = Depends(get_db),
):
    approval = _get_approval(
        approval_id,
        db,
    )

    # --------------------------------------------------------
    # Approval must already be approved
    # --------------------------------------------------------

    if approval.status != "APPROVED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Approval must be APPROVED before execution. "
                f"Current status: {approval.status}"
            ),
        )

    # --------------------------------------------------------
    # Prevent duplicate execution
    # --------------------------------------------------------

    existing_execution = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.run_id == approval.run_id,
            AuditEvent.event_type
            == "approval.execution_completed",
        )
        .first()
    )

    if existing_execution:
        raise HTTPException(
            status_code=409,
            detail="Approval has already been executed",
        )

    # --------------------------------------------------------
    # Execute approved action
    # --------------------------------------------------------

    service = ApprovalExecutionService()

    try:
        return service.execute_approved(
            db,
            approval,
        )

    except ActionExecutionError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# ============================================================
# Get Approval Execution
# ============================================================

@router.get("/approvals/{approval_id}/execution")
def get_approval_execution(
    approval_id: str,
    db: Session = Depends(get_db),
):
    approval = _get_approval(
        approval_id,
        db,
    )

    service = ApprovalExecutionService()

    try:
        execution = service.get_execution(
            db,
            approval,
        )

    except ActionExecutionError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "execution_id": execution.execution_id,
        "approval_id": execution.approval_id,
        "run_id": execution.run_id,
        "status": execution.status,
        "execution_mode": execution.execution_mode,
        "created_at": execution.created_at,
        "completed_at": execution.completed_at,
        "result": execution.result,
    }