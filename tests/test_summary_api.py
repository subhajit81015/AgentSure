from fastapi.testclient import TestClient

from agentsure.db import Base, SessionLocal, engine
from agentsure.main import app
from agentsure.models import EvaluationRun

client = TestClient(app)


def test_get_run_summary():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    existing = db.get(EvaluationRun, "summary-test-run")

    if existing:
        db.delete(existing)
        db.commit()

    run = EvaluationRun(
        id="summary-test-run",
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
        summary={
            "case_count": 1,
            "approval_score": 100.0,
        },
    )

    db.add(run)
    db.commit()
    db.close()

    response = client.get(
        "/v1/runs/summary-test-run/summary"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["run_id"] == "summary-test-run"
    assert body["agent"]["id"] == "test-agent"
    assert body["decision"]["release"] == "GO"
    assert body["scores"]["arai"] == 100.0
    assert body["risk"]["critical_failures"] == 0
    assert body["risk"]["human_approval_required"] is False


def test_get_run_summary_for_missing_run():
    response = client.get(
        "/v1/runs/does-not-exist/summary"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation run not found"