from fastapi.testclient import TestClient

from agentsure.db import Base, SessionLocal, engine
from agentsure.main import app
from agentsure.models import AuditEvent, EvaluationRun

client = TestClient(app)


def test_get_audit_events_for_existing_run():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    existing_run = db.get(EvaluationRun, "audit-test-run")
    if existing_run:
        db.query(AuditEvent).filter(
            AuditEvent.run_id == "audit-test-run"
        ).delete()
        db.delete(existing_run)
        db.commit()

    run = EvaluationRun(
        id="audit-test-run",
        agent_id="test-agent",
        model_version="test-model",
        prompt_version="test-prompt",
        dataset_version="test-dataset",
        test_suite_version="v1",
        quality_score=100.0,
        safety_score=100.0,
        reliability_score=100.0,
        operations_score=100.0,
        arai_score=100.0,
        release_decision="GO",
        critical_failure_count=0,
        summary={"case_count": 1},
    )

    db.add(run)

    db.add(
        AuditEvent(
            run_id=run.id,
            event_type="agent.run",
            payload={"agent_id": "test-agent"},
        )
    )

    db.add(
        AuditEvent(
            run_id=run.id,
            event_type="evaluation.completed",
            payload={"arai_score": 100.0},
        )
    )

    db.commit()
    db.close()

    response = client.get("/v1/audit/audit-test-run")

    assert response.status_code == 200

    body = response.json()

    assert body["run_id"] == "audit-test-run"
    assert body["event_count"] == 2
    assert body["events"][0]["event_type"] == "agent.run"
    assert body["events"][1]["event_type"] == "evaluation.completed"

    db = SessionLocal()
    db.query(AuditEvent).filter(
        AuditEvent.run_id == "audit-test-run"
    ).delete()
    run = db.get(EvaluationRun, "audit-test-run")
    if run:
        db.delete(run)
    db.commit()
    db.close()


def test_get_audit_events_for_missing_run():
    response = client.get("/v1/audit/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation run not found"

def test_get_audit_events_for_existing_run_with_no_events():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    existing_run = db.get(EvaluationRun, "audit-empty-run")
    if existing_run:
        db.query(AuditEvent).filter(
            AuditEvent.run_id == "audit-empty-run"
        ).delete()
        db.delete(existing_run)
        db.commit()

    run = EvaluationRun(
        id="audit-empty-run",
        agent_id="test-agent",
        model_version="test-model",
        prompt_version="test-prompt",
        dataset_version="test-dataset",
        test_suite_version="v1",
        quality_score=100.0,
        safety_score=100.0,
        reliability_score=100.0,
        operations_score=100.0,
        arai_score=100.0,
        release_decision="GO",
        critical_failure_count=0,
        summary={"case_count": 0},
    )

    db.add(run)
    db.commit()
    db.close()

    response = client.get("/v1/audit/audit-empty-run")

    assert response.status_code == 200

    body = response.json()

    assert body["run_id"] == "audit-empty-run"
    assert body["event_count"] == 0
    assert body["events"] == []

    db = SessionLocal()
    db.delete(db.get(EvaluationRun, "audit-empty-run"))
    db.commit()
    db.close()