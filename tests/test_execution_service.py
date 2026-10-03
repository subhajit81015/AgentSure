from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agentsure.db import SessionLocal
from agentsure.execution_service import ApprovalExecutionService
from agentsure.models import AuditEvent


def build_approved_approval():
    approval_id = f"TEST-APPROVAL-{uuid4()}"
    run_id = f"TEST-RUN-{uuid4()}"

    return SimpleNamespace(
        approval_id=approval_id,
        run_id=run_id,
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
            datetime.now(UTC)
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
                AuditEvent.run_id == approval.run_id,
                AuditEvent.event_type
                == "approval.execution_completed",
            )
            .order_by(AuditEvent.id.desc())
            .first()
        )

        assert event is not None
        assert event.payload["approval_id"] == approval.approval_id
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


def test_action_no_longer_requires_human_approval_is_blocked():
    approval = build_approved_approval()

    approval.normalized_parameters = {
        "requested_actions": [
            "update_ticket",
        ],
    }

    db = SessionLocal()

    try:
        service = ApprovalExecutionService()

        with pytest.raises(
            ValueError,
            match="no longer classified as high-impact",
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
        datetime.now(UTC)
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


def test_execution_audit_contains_policy_and_execution_details():
    db = SessionLocal()

    try:
        approval = build_approved_approval()
        service = ApprovalExecutionService()

        result = service.execute_approved(
            db,
            approval,
        )

        assert result["status"] == "SIMULATED_SUCCESS"

        event = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.run_id == approval.run_id,
                AuditEvent.event_type
                == "approval.execution_completed",
            )
            .order_by(AuditEvent.id.desc())
            .first()
        )

        assert event is not None

        assert event.payload["approval_id"] == (
            approval.approval_id
        )

        assert event.payload["agent_id"] == (
            approval.agent_id
        )

        assert event.payload["incident_id"] == (
            approval.incident_id
        )

        assert event.payload["approval_action"] == (
            approval.action
        )

        assert event.payload["risk_level"] == (
            approval.risk_level
        )

        assert event.payload["target"] == (
            approval.target
        )

        assert event.payload["policy_version"] == (
            approval.policy_version
        )

        assert event.payload["execution_mode"] == "SIMULATED"

        assert event.payload["requested_actions"] == [
            "reset_password",
            "delete_old_credentials",
        ]

        assert len(event.payload["executions"]) == 2

        for execution in event.payload["executions"]:
            assert execution["status"] == "SIMULATED_SUCCESS"
            assert execution["simulated"] is True

    finally:
        db.close()