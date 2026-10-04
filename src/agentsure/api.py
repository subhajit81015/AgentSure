from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import AuditEvent, EvaluationRun
from .schemas import EvaluationRequest, EvaluationResponse
from .service import run_evaluation

router = APIRouter(prefix="/v1")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/evaluations", response_model=EvaluationResponse, status_code=201)
def create_evaluation(
    request: EvaluationRequest,
    db: Session = Depends(get_db),
):
    run = run_evaluation(db, request)

    return EvaluationResponse(
        run_id=run.id,
        arai_score=run.arai_score,
        release_decision=run.release_decision,
        critical_failure_count=run.critical_failure_count,
        summary=run.summary,
    )


@router.get("/evaluations/{run_id}")
def get_evaluation(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = db.get(EvaluationRun, run_id)

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found",
        )

    return {
        "run_id": run.id,
        "agent_id": run.agent_id,
        "model_version": run.model_version,
        "arai_score": run.arai_score,
        "release_decision": run.release_decision,
        "critical_failure_count": run.critical_failure_count,
        "summary": run.summary,
        "created_at": run.created_at,
    }


@router.get("/audit/{run_id}")
def get_audit_events(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = db.get(EvaluationRun, run_id)

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found",
        )

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.run_id == run_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )

    return {
        "run_id": run_id,
        "event_count": len(events),
        "events": [
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }
@router.get("/runs/{run_id}/assurance")
def get_run_assurance(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = db.get(EvaluationRun, run_id)

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found",
        )

    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.run_id == run_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )

    from .models import ApprovalExecution, ApprovalRecord

    approval = (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.run_id == run_id)
        .order_by(ApprovalRecord.requested_at.desc())
        .first()
    )

    execution = None

    if approval:
        execution = (
            db.query(ApprovalExecution)
            .filter(
                ApprovalExecution.approval_id
                == approval.approval_id
            )
            .first()
        )

    return {
        "run_id": run.id,
        "agent_id": run.agent_id,
        "evaluation": {
            "model_version": run.model_version,
            "arai_score": run.arai_score,
            "quality_score": run.quality_score,
            "safety_score": run.safety_score,
            "reliability_score": run.reliability_score,
            "operations_score": run.operations_score,
            "release_decision": run.release_decision,
            "critical_failure_count": run.critical_failure_count,
        },
        "approval": (
            {
                "required": True,
                "approval_id": approval.approval_id,
                "status": approval.status,
                "risk_level": approval.risk_level,
                "action": approval.action,
                "incident_id": approval.incident_id,
                "decided_by": approval.decided_by,
                "decision_reason": approval.decision_reason,
                "requested_at": approval.requested_at,
                "decided_at": approval.decided_at,
            }
            if approval
            else {
                "required": False,
            }
        ),
        "execution": (
            {
                "execution_id": execution.execution_id,
                "status": execution.status,
                "execution_mode": execution.execution_mode,
                "result": execution.result,
                "created_at": execution.created_at,
                "completed_at": execution.completed_at,
            }
            if execution
            else None
        ),
        "audit": {
            "event_count": len(audit_events),
            "events": [
                {
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }
                for event in audit_events
            ],
        },
    }