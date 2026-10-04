from agentsure.policy import RiskDecision, evaluate_risk


def test_high_impact_action_requires_human_approval():
    result = evaluate_risk(
        critical_failure_count=0,
        approval_required=True,
        approval_risk_level="high",
        arai_score=100.0,
    )

    assert isinstance(result, RiskDecision)
    assert result.level == "HIGH"
    assert result.human_approval_required is True
    assert result.release_decision == "CONDITIONAL GO"
    assert (
        result.reason
        == "High-impact action requires human approval before execution."
    )


def test_critical_failure_blocks_release():
    result = evaluate_risk(
        critical_failure_count=1,
        approval_required=False,
        approval_risk_level=None,
        arai_score=100.0,
    )

    assert result.level == "CRITICAL"
    assert result.human_approval_required is False
    assert result.release_decision == "NO-GO"
    assert result.reason == "Critical evaluation failures detected."


def test_low_arai_requires_conditional_go():
    result = evaluate_risk(
        critical_failure_count=0,
        approval_required=False,
        approval_risk_level=None,
        arai_score=60.0,
    )

    assert result.level == "HIGH"
    assert result.human_approval_required is True
    assert result.release_decision == "CONDITIONAL GO"
    assert result.reason == "ARAI score is below the acceptable threshold."


def test_clean_evaluation_is_low_risk():
    result = evaluate_risk(
        critical_failure_count=0,
        approval_required=False,
        approval_risk_level=None,
        arai_score=100.0,
    )

    assert result.level == "LOW"
    assert result.human_approval_required is False
    assert result.release_decision == "GO"
    assert result.reason == "Evaluation passed without blocking conditions."


def test_approval_risk_level_is_normalized_to_uppercase():
    result = evaluate_risk(
        critical_failure_count=0,
        approval_required=True,
        approval_risk_level="medium",
        arai_score=100.0,
    )

    assert result.level == "MEDIUM"
    assert result.human_approval_required is True
    assert result.release_decision == "CONDITIONAL GO"