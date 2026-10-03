from agentsure.authorization import authorize_action


def test_authorizes_low_risk_action():
    decision = authorize_action(
        actor="employee-2048",
        action="read_ticket",
        risk_level="low",
    )

    assert decision.allowed is True
    assert decision.reason == "Action authorized."


def test_authorizes_medium_risk_action():
    decision = authorize_action(
        actor="employee-2048",
        action="update_ticket",
        risk_level="medium",
    )

    assert decision.allowed is True
    assert decision.reason == "Action authorized."


def test_requires_human_approval_for_high_risk_action():
    decision = authorize_action(
        actor="employee-2048",
        action="reset_password",
        risk_level="high",
    )

    assert decision.allowed is False
    assert "human approval" in decision.reason


def test_requires_human_approval_for_critical_risk_action():
    decision = authorize_action(
        actor="employee-2048",
        action="delete_credentials",
        risk_level="critical",
    )

    assert decision.allowed is False
    assert "human approval" in decision.reason


def test_rejects_missing_actor():
    decision = authorize_action(
        actor="",
        action="read_ticket",
        risk_level="low",
    )

    assert decision.allowed is False
    assert decision.reason == "Actor is required."


def test_rejects_missing_action():
    decision = authorize_action(
        actor="employee-2048",
        action="",
        risk_level="low",
    )

    assert decision.allowed is False
    assert decision.reason == "Action is required."


def test_rejects_invalid_risk_level():
    decision = authorize_action(
        actor="employee-2048",
        action="read_ticket",
        risk_level="unknown",
    )

    assert decision.allowed is False
    assert decision.reason == "Invalid risk level."