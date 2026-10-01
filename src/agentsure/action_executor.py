from dataclasses import dataclass
from typing import Any


ALLOWED_SIMULATED_ACTIONS = frozenset(
    {
        "reset_password",
        "delete_old_credentials",
    }
)


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    action: str
    simulated: bool
    target: str | None
    message: str


class ActionExecutionError(ValueError):
    """Raised when a requested action cannot be safely executed."""


class SimulatedActionExecutor:
    """
    Safe execution boundary for AgentSure.

    This implementation deliberately performs no external side effects.
    It only validates the action and returns a deterministic simulation result.
    """

    def execute(
        self,
        *,
        action: str,
        parameters: dict[str, Any],
        approved: bool,
    ) -> ExecutionResult:
        if not approved:
            raise ActionExecutionError(
                "Execution requires explicit approval."
            )

        if action not in ALLOWED_SIMULATED_ACTIONS:
            raise ActionExecutionError(
                f"Action is not allowlisted: {action}"
            )

        target = parameters.get("target")

        return ExecutionResult(
            status="SIMULATED_SUCCESS",
            action=action,
            simulated=True,
            target=target,
            message=(
                f"Simulated execution completed for "
                f"action '{action}'. No external side effect occurred."
            ),
        )