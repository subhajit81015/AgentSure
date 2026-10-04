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