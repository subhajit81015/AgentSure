from agentsure.evaluators import evaluate_case
from agentsure.schemas import EvaluationCase
from agentsure.scoring import calculate_scores


def test_security_failure_blocks_release():
    cases = [
        EvaluationCase(case_id="s1", category="security", prompt_injection=True),
        EvaluationCase(case_id="q1", category="quality", response_text="invoice 123", expected_answer_keywords=["invoice"]),
    ]
    results = [evaluate_case(c) for c in cases]
    scores = calculate_scores(results)
    assert scores["release_decision"] == "NO-GO"
    assert scores["critical_failure_count"] == 1
