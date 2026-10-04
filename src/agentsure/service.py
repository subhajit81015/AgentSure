from uuid import uuid4

from sqlalchemy.orm import Session

from .evaluators import evaluate_case
from .models import AuditEvent, EvaluationResult, EvaluationRun
from .policy import evaluate_risk
from .schemas import EvaluationRequest
from .scoring import calculate_scores


def run_evaluation(
    db: Session,
    request: EvaluationRequest,
) -> EvaluationRun:
    run_id = str(uuid4())

    results = [
        evaluate_case(case)
        for case in request.cases
    ]

    scores = calculate_scores(results)

    # Determine whether any evaluation case requires
    # human approval before execution.
    approval_cases = [
        case
        for case in request.cases
        if case.approval_required
    ]

    approval_required = bool(approval_cases)

    approval_risk_level = next(
        (
            case.approval_risk_level
            for case in approval_cases
            if case.approval_risk_level
        ),
        None,
    )

    risk = evaluate_risk(
        critical_failure_count=scores["critical_failure_count"],
        approval_required=approval_required,
        approval_risk_level=approval_risk_level,
        arai_score=scores["arai_score"],
    )

    summary = {
        "case_count": len(results),
        **scores,
        "policy": {
            "risk_level": risk.level,
            "human_approval_required": risk.human_approval_required,
            "release_decision": risk.release_decision,
            "reason": risk.reason,
        },
    }

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
        release_decision=risk.release_decision,
        critical_failure_count=scores["critical_failure_count"],
        summary=summary,
    )

    db.add(run)

    for result in results:
        db.add(
            EvaluationResult(
                run_id=run_id,
                case_id=result.case_id,
                category=result.category,
                passed=result.passed,
                critical=result.critical,
                score=result.score,
                findings=result.findings,
            )
        )

    db.add(
        AuditEvent(
            run_id=run_id,
            event_type="evaluation.completed",
            payload={
                **scores,
                "case_count": len(results),
                "policy": {
                    "risk_level": risk.level,
                    "human_approval_required": (
                        risk.human_approval_required
                    ),
                    "release_decision": risk.release_decision,
                    "reason": risk.reason,
                },
            },
        )
    )

    db.commit()
    db.refresh(run)

    return run