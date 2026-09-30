from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from agentsure.main import app
from agentsure.db import SessionLocal
from agentsure.models import ApprovalRecord, AuditEvent


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
            datetime.now(timezone.utc)
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