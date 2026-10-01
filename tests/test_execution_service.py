from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from agentsure.db import SessionLocal
from agentsure.execution_service import ApprovalExecutionService
from agentsure.models import AuditEvent


def build_approved_approval():
    return SimpleNamespace(
        approval_id="TEST-APPROVAL-001",
        run_id="TEST-RUN-001",
        agent_id="serviceops-agent-v1",
        incident_id="INC-10452",
        action="high-impact-action",
        risk_level="high",
        target={
            "type": "incident",
            "id": "INC-10452",
        },
        normalized_parameters={
            "requested_actions": [
                "reset_password",
                "delete_old_credentials",
            ],
        },
        policy_version="serviceops-approval-v1",
        status="APPROVED",
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=5)
        ),
    )


def test_approved_request_executes_as_simulation():
    db = SessionLocal()

    try:
        approval = build_approved_approval()

        service = ApprovalExecutionService()

        result = service.execute_approved(
            db,
            approval,
        )

        assert result["status"] == "SIMULATED_SUCCESS"
        assert result["simulated"] is True

        assert {
            item["action"]
            for item in result["actions"]
        } == {
            "reset_password",
            "delete_old_credentials",
        }

        for item in result["actions"]:
            assert item["status"] == "SIMULATED_SUCCESS"
            assert item["simulated"] is True

        event = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.run_id == "TEST-RUN-001",
                AuditEvent.event_type
                == "approval.execution_completed",
            )
            .order_by(AuditEvent.id.desc())
            .first()
        )

        assert event is not None
        assert event.payload["approval_id"] == "TEST-APPROVAL-001"
        assert event.payload["requested_actions"] == [
            "reset_password",
            "delete_old_credentials",
        ]
        assert event.payload["execution_mode"] == "SIMULATED"

    finally:
        db.close()


def test_unapproved_request_cannot_execute():
    approval = build_approved_approval()
    approval.status = "PENDING_APPROVAL"

    db = SessionLocal()

    try:
        service = ApprovalExecutionService()

        with pytest.raises(
            ValueError,
            match="Only APPROVED",
        ):
            service.execute_approved(
                db,
                approval,
            )
    finally:
        db.close()


def test_unregistered_action_is_blocked_by_policy():
    approval = build_approved_approval()

    approval.normalized_parameters = {
        "requested_actions": [
            "unknown_sensitive_action",
        ],
    }

    db = SessionLocal()

    try:
        service = ApprovalExecutionService()

        with pytest.raises(
            ValueError,
            match="not registered by agent policy",
        ):
            service.execute_approved(
                db,
                approval,
            )
    finally:
        db.close()


def test_stale_policy_version_is_blocked():
    approval = build_approved_approval()
    approval.policy_version = "serviceops-approval-v0"

    db = SessionLocal()

    try:
        service = ApprovalExecutionService()

        with pytest.raises(
            ValueError,
            match="policy version is no longer current",
        ):
            service.execute_approved(
                db,
                approval,
            )
    finally:
        db.close()


def test_expired_approved_request_is_blocked():
    approval = build_approved_approval()

    approval.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )

    db = SessionLocal()

    try:
        service = ApprovalExecutionService()

        with pytest.raises(
            ValueError,
            match="Approval has expired",
        ):
            service.execute_approved(
                db,
                approval,
            )
    finally:
        db.close()