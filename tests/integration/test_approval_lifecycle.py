from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from agentsure.db import SessionLocal
from agentsure.main import app
from agentsure.models import (
    ApprovalExecution,
    ApprovalRecord,
    AuditEvent,
)

client = TestClient(app)


def create_pending_approval():
    response = client.post(
        "/v1/agents/serviceops/run",
        json={
            "incident_id": "INC-10452",
            "user_message": (
                "Please reset my password immediately "
                "and delete the old credentials."
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "PENDING_APPROVAL"
    assert body["approval"] is not None
    assert body["approval"]["status"] == "PENDING_APPROVAL"

    return body


def test_get_pending_approval():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]

    response = client.get(
        f"/v1/approvals/{approval_id}"
    )

    assert response.status_code == 200

    approval = response.json()

    assert approval["approval_id"] == approval_id
    assert approval["status"] == "PENDING_APPROVAL"
    assert approval["incident_id"] == "INC-10452"


def test_approve_request_and_audit_event():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]
    run_id = body["run_id"]

    response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={
            "decided_by": "admin@example.com",
            "reason": "Verified user identity and approved.",
        },
    )

    assert response.status_code == 200

    approval = response.json()

    assert approval["status"] == "APPROVED"
    assert approval["decided_by"] == "admin@example.com"
    assert (
        approval["decision_reason"]
        == "Verified user identity and approved."
    )
    assert approval["decided_at"] is not None

    db = SessionLocal()

    try:
        event = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.run_id == run_id,
                AuditEvent.event_type == "approval.approved",
            )
            .order_by(AuditEvent.id.desc())
            .first()
        )

        assert event is not None
        assert event.payload["approval_id"] == approval_id
        assert event.payload["decided_by"] == "admin@example.com"

    finally:
        db.close()


def test_reject_request_and_audit_event():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]
    run_id = body["run_id"]

    response = client.post(
        f"/v1/approvals/{approval_id}/reject",
        json={
            "decided_by": "security@example.com",
            "reason": "Request rejected by security policy.",
        },
    )

    assert response.status_code == 200

    approval = response.json()

    assert approval["status"] == "REJECTED"
    assert approval["decided_by"] == "security@example.com"
    assert (
        approval["decision_reason"]
        == "Request rejected by security policy."
    )
    assert approval["decided_at"] is not None

    db = SessionLocal()

    try:
        event = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.run_id == run_id,
                AuditEvent.event_type == "approval.rejected",
            )
            .order_by(AuditEvent.id.desc())
            .first()
        )

        assert event is not None
        assert event.payload["approval_id"] == approval_id
        assert event.payload["decided_by"] == "security@example.com"

    finally:
        db.close()


def test_resolved_approval_cannot_be_approved_twice():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]

    first_response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={
            "decided_by": "admin@example.com",
            "reason": "Approved.",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "APPROVED"

    second_response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={
            "decided_by": "another-admin@example.com",
            "reason": "Duplicate approval attempt.",
        },
    )

    assert second_response.status_code == 409
    assert "already resolved" in second_response.json()["detail"]


def test_expired_approval_is_persisted():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]

    db = SessionLocal()

    try:
        approval = db.get(
            ApprovalRecord,
            approval_id,
        )

        assert approval is not None

        approval.expires_at = (
            datetime.now(UTC)
            - timedelta(seconds=1)
        )

        db.commit()

    finally:
        db.close()

    response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={
            "decided_by": "admin@example.com",
            "reason": "Attempted after expiration.",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Approval has expired"

    db = SessionLocal()

    try:
        approval = db.get(
            ApprovalRecord,
            approval_id,
        )

        assert approval is not None
        assert approval.status == "EXPIRED"

    finally:
        db.close()


def test_approved_request_can_be_executed_once():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]

    approve_response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={
            "decided_by": "admin@example.com",
            "reason": "Approved for controlled execution.",
        },
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"

    execute_response = client.post(
        f"/v1/approvals/{approval_id}/execute"
    )

    assert execute_response.status_code == 200

    execution = execute_response.json()

    assert execution["approval_id"] == approval_id
    assert execution["status"] == "SIMULATED_SUCCESS"
    assert execution["simulated"] is True

    actions = {
        item["action"]
        for item in execution["actions"]
    }

    assert actions == {
        "reset_password",
        "delete_old_credentials",
    }

    for item in execution["actions"]:
        assert item["status"] == "SIMULATED_SUCCESS"
        assert item["simulated"] is True

    assert (
        "No external side effects occurred."
        in execution["message"]
    )

    second_execute_response = client.post(
        f"/v1/approvals/{approval_id}/execute"
    )

    assert second_execute_response.status_code == 409
    assert (
        second_execute_response.json()["detail"]
        == "Approval has already been executed"
    )
def test_execution_is_persisted_and_can_be_retrieved():
    body = create_pending_approval()

    approval_id = body["approval"]["approval_id"]
    run_id = body["run_id"]

    approve_response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={
            "decided_by": "admin@example.com",
            "reason": "Approved for controlled execution.",
        },
    )

    assert approve_response.status_code == 200

    execute_response = client.post(
        f"/v1/approvals/{approval_id}/execute"
    )

    assert execute_response.status_code == 200

    execution_response = execute_response.json()

    assert execution_response["status"] == "SIMULATED_SUCCESS"

    execution_id = execution_response["execution_id"]

    db = SessionLocal()

    try:
        execution = db.get(
            ApprovalExecution,
            execution_id,
        )

        assert execution is not None
        assert execution.approval_id == approval_id
        assert execution.run_id == run_id
        assert execution.status == "SIMULATED_SUCCESS"
        assert execution.execution_mode == "SIMULATED"
        assert execution.completed_at is not None
        assert execution.result is not None

    finally:
        db.close()

    lookup_response = client.get(
        f"/v1/approvals/{approval_id}/execution"
    )

    assert lookup_response.status_code == 200

    lookup = lookup_response.json()

    assert lookup["execution_id"] == execution_id
    assert lookup["approval_id"] == approval_id
    assert lookup["run_id"] == run_id
    assert lookup["status"] == "SIMULATED_SUCCESS"
    assert lookup["execution_mode"] == "SIMULATED"
    assert lookup["completed_at"] is not None