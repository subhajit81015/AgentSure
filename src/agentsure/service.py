from uuid import uuid4

from sqlalchemy.orm import Session

from .evaluators import evaluate_case
from .models import AuditEvent, EvaluationResult, EvaluationRun
from .schemas import EvaluationRequest
from .scoring import calculate_scores


def run_evaluation(db: Session, request: EvaluationRequest) -> EvaluationRun:
    run_id = str(uuid4())
    results = [evaluate_case(case) for case in request.cases]
    scores = calculate_scores(results)

    run = EvaluationRun(
        id=run_id,
        agent_id=request.agent_id,
        model_version=request.model_version,
        prompt_version=request.prompt_version,
        dataset_version=request.dataset_version,
        test_suite_version=request.test_suite_version,
        quality_score=scores["quality_score"],
        safety_score=scores["safety_score"],
        reliability_score=scores["reliability_score"],
        operations_score=scores["operations_score"],
        arai_score=scores["arai_score"],
        release_decision=scores["release_decision"],
        critical_failure_count=scores["critical_failure_count"],
        summary={"case_count": len(results), **scores},
    )
    db.add(run)
    for result in results:
        db.add(EvaluationResult(
            run_id=run_id,
            case_id=result.case_id,
            category=result.category,
            passed=result.passed,
            critical=result.critical,
            score=result.score,
            findings=result.findings,
        ))
    db.add(AuditEvent(run_id=run_id, event_type="evaluation.completed", payload={**scores, "case_count": len(results)}))
    db.commit()
    db.refresh(run)
    return run
