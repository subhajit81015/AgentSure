import pytest

from agentsure.action_executor import (
    ActionExecutionError,
    SimulatedActionExecutor,
)


def test_approved_reset_password_is_simulated():
    executor = SimulatedActionExecutor()

    result = executor.execute(
        action="reset_password",
        parameters={
            "target": "INC-10452",
        },
        approved=True,
    )

    assert result.status == "SIMULATED_SUCCESS"
    assert result.action == "reset_password"
    assert result.simulated is True
    assert result.target == "INC-10452"
    assert "No external side effect occurred." in result.message


def test_unapproved_action_is_blocked():
    executor = SimulatedActionExecutor()

    with pytest.raises(
        ActionExecutionError,
        match="requires explicit approval",
    ):
        executor.execute(
            action="reset_password",
            parameters={
                "target": "INC-10452",
            },
            approved=False,
        )


def test_non_allowlisted_action_is_blocked():
    executor = SimulatedActionExecutor()

    with pytest.raises(
        ActionExecutionError,
        match="not allowlisted",
    ):
        executor.execute(
            action="disable_account",
            parameters={
                "target": "INC-10452",
            },
            approved=True,
        )