from agentsure.policy import evaluate_risk


def test_critical_failure_blocks_release():
    decision = evaluate_risk(
        critical_failure_count=1,
        approval_required=False,
        approval_risk_level=None,
        arai_score=100.0,
    )

    assert decision.level == "CRITICAL"
    assert decision.release_decision == "NO-GO"
    assert decision.human_approval_required is False


def test_high_impact_action_requires_approval():
    decision = evaluate_risk(
        critical_failure_count=0,
        approval_required=True,
        approval_risk_level="high",
        arai_score=100.0,
    )

    assert decision.level == "HIGH"
    assert decision.release_decision == "CONDITIONAL GO"
    assert decision.human_approval_required is True


def test_low_arai_requires_review():
    decision = evaluate_risk(
        critical_failure_count=0,
        approval_required=False,
        approval_risk_level=None,
        arai_score=60.0,
    )

    assert decision.level == "HIGH"
    assert decision.release_decision == "CONDITIONAL GO"
    assert decision.human_approval_required is True


def test_clean_run_is_low_risk():
    decision = evaluate_risk(
        critical_failure_count=0,
        approval_required=False,
        approval_risk_level=None,
        arai_score=100.0,
    )

    assert decision.level == "LOW"
    assert decision.release_decision == "GO"
    assert decision.human_approval_required is False