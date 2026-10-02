from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    agent_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )

    model_version: Mapped[str] = mapped_column(
        String(128),
    )

    prompt_version: Mapped[str] = mapped_column(
        String(128),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(128),
    )

    test_suite_version: Mapped[str] = mapped_column(
        String(128),
    )

    quality_score: Mapped[float] = mapped_column(Float)
    safety_score: Mapped[float] = mapped_column(Float)
    reliability_score: Mapped[float] = mapped_column(Float)
    operations_score: Mapped[float] = mapped_column(Float)
    arai_score: Mapped[float] = mapped_column(Float)

    release_decision: Mapped[str] = mapped_column(
        String(32),
    )

    critical_failure_count: Mapped[int] = mapped_column(
        Integer,
    )

    summary: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    case_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(64),
    )

    passed: Mapped[bool]
    critical: Mapped[bool]
    score: Mapped[float]

    findings: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
    )

    payload: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )


class ApprovalRecord(Base):
    """Persistent human-in-the-loop approval state."""

    __tablename__ = "approval_records"

    approval_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )

    incident_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(128),
    )

    action: Mapped[str] = mapped_column(
        String(128),
    )

    risk_level: Mapped[str] = mapped_column(
        String(32),
    )

    target: Mapped[dict] = mapped_column(JSON)

    normalized_parameters: Mapped[dict] = mapped_column(
        JSON,
    )

    policy_version: Mapped[str] = mapped_column(
        String(128),
    )

    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    decided_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

class ApprovalExecution(Base):
    """Tracks the single execution attempt for an approved request."""

    __tablename__ = "approval_executions"

    __table_args__ = (
        UniqueConstraint(
            "approval_id",
            name="uq_approval_execution_approval_id",
        ),
    )

    execution_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    approval_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
    )

    execution_mode: Mapped[str] = mapped_column(
        String(32),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    result: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )
