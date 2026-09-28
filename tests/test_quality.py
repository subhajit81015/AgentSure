from agentsure.evaluators import quality_eval
from agentsure.schemas import EvaluationCase


def test_quality_keyword_coverage():
    c = EvaluationCase(case_id="q1", category="quality", response_text="invoice ledger 12500", expected_answer_keywords=["invoice","ledger","12500"], grounded=True, citation_valid=True)
    r = quality_eval(c)
    assert r.passed is True
    assert r.score >= 90
