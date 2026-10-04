from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agentsure.db import Base
from agentsure.models import AuditEvent, EvaluationResult, EvaluationRun
from agentsure.schemas import EvaluationCase, EvaluationRequest
from agentsure.service import run_evaluation


def create_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    return session_local()


def build_request(cases=None):
    if cases is None:
        cases = [
            EvaluationCase(
                case_id="case-001",
                category="quality",
                response_text="Python is a programming language.",
                expected_answer_keywords=[
                    "Python",
                    "programming language",
                ],
                grounded=True,
                citation_valid=True,
            )
        ]

    return EvaluationRequest(
        agent_id="test-agent",
        model_version="test-model",
        prompt_version="prompt-v1",
        dataset_version="dataset-v1",
        test_suite_version="suite-v1",
        cases=cases,
    )


def test_run_evaluation_creates_evaluation_run():
    db = create_test_db()

    try:
        run = run_evaluation(
            db,
            build_request(),
        )

        assert run.id is not None
        assert run.agent_id == "test-agent"
        assert run.model_version == "test-model"
        assert run.release_decision == "GO"
        assert run.critical_failure_count == 0
        assert run.arai_score == 100.0

        stored_run = db.get(
            EvaluationRun,
            run.id,
        )

        assert stored_run is not None
    finally:
        db.close()


def test_run_evaluation_persists_audit_event():
    db = create_test_db()

    try:
        run = run_evaluation(
            db,
            build_request(),
        )

        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.run_id == run.id)
            .all()
        )

        assert len(events) == 1
        assert events[0].event_type == "evaluation.completed"
        assert events[0].payload["case_count"] == 1
        assert events[0].payload["policy"]["risk_level"] == "LOW"
        assert (
            events[0].payload["policy"]["human_approval_required"]
            is False
        )
        assert events[0].payload["policy"]["release_decision"] == "GO"
    finally:
        db.close()


def test_run_evaluation_persists_evaluation_results():
    db = create_test_db()

    try:
        run = run_evaluation(
            db,
            build_request(),
        )

        results = (
            db.query(EvaluationResult)
            .filter(EvaluationResult.run_id == run.id)
            .all()
        )

        assert len(results) == 1
        assert results[0].case_id == "case-001"
        assert results[0].category == "quality"
        assert results[0].passed is True
        assert results[0].critical is False
        assert results[0].score == 100.0
    finally:
        db.close()


def test_run_evaluation_stores_case_count_in_summary():
    db = create_test_db()

    try:
        run = run_evaluation(
            db,
            build_request(),
        )

        assert run.summary["case_count"] == 1
        assert run.summary["quality_score"] == 100.0
        assert run.summary["policy"]["risk_level"] == "LOW"
        assert (
            run.summary["policy"]["human_approval_required"]
            is False
        )
        assert run.summary["policy"]["release_decision"] == "GO"
    finally:
        db.close()