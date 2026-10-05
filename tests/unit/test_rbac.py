from agentsure.rbac import authorize


def test_operator_can_read_approval():
    decision = authorize(
        "operator",
        "approval.read",
    )

    assert decision.allowed is True
    assert decision.reason == "Permission granted."


def test_operator_cannot_approve():
    decision = authorize(
        "operator",
        "approval.approve",
    )

    assert decision.allowed is False


def test_reviewer_can_approve():
    decision = authorize(
        "reviewer",
        "approval.approve",
    )

    assert decision.allowed is True


def test_reviewer_can_reject():
    decision = authorize(
        "reviewer",
        "approval.reject",
    )

    assert decision.allowed is True


def test_reviewer_cannot_execute():
    decision = authorize(
        "reviewer",
        "execution.execute",
    )

    assert decision.allowed is False


def test_admin_can_execute():
    decision = authorize(
        "admin",
        "execution.execute",
    )

    assert decision.allowed is True


def test_unknown_role_is_rejected():
    decision = authorize(
        "unknown",
        "approval.approve",
    )

    assert decision.allowed is False
    assert decision.reason == "Unknown role."


def test_empty_role_is_rejected():
    decision = authorize(
        "",
        "approval.approve",
    )

    assert decision.allowed is False
    assert decision.reason == "Role is required."