from typing import Any

from sqlalchemy.orm import Session

from .action_executor import (
    ActionExecutionError,
    SimulatedActionExecutor,
)
from .models import ApprovalRecord, AuditEvent


class ApprovalExecutionService:
    def __init__(self):
        self.executor = SimulatedActionExecutor()

    def execute_approved(
        self,
        db: Session,
        approval: ApprovalRecord,
    ) -> dict[str, Any]:
        if approval.status != "APPROVED":
            raise ActionExecutionError(
                "Only APPROVED requests can be executed."
            )

        parameters = approval.normalized_parameters or {}

        requested_actions = parameters.get(
            "requested_actions",
            [],
        )

        if not isinstance(requested_actions, list):
            raise ActionExecutionError(
                "Approved requested_actions must be a list."
            )

        if not requested_actions:
            raise ActionExecutionError(
                "No approved concrete actions were provided."
            )

        executions = []

        for action in requested_actions:
            if not isinstance(action, str):
                raise ActionExecutionError(
                    "Each approved action must be a string."
                )

            result = self.executor.execute(
                action=action,
                parameters={
                    "target": approval.target,
                },
                approved=True,
            )

            executions.append(
                {
                    "action": result.action,
                    "status": result.status,
                    "simulated": result.simulated,
                    "target": result.target,
                    "message": result.message,
                }
            )

        db.add(
            AuditEvent(
                run_id=approval.run_id,
                event_type="approval.execution_completed",
                payload={
                    "approval_id": approval.approval_id,
                    "agent_id": approval.agent_id,
                    "incident_id": approval.incident_id,
                    "approval_action": approval.action,
                    "requested_actions": requested_actions,
                    "risk_level": approval.risk_level,
                    "target": approval.target,
                    "policy_version": approval.policy_version,
                    "execution_mode": "SIMULATED",
                    "executions": executions,
                },
            )
        )

        db.commit()

        return {
            "approval_id": approval.approval_id,
            "status": "SIMULATED_SUCCESS",
            "simulated": True,
            "actions": executions,
            "message": (
                "All approved actions were simulated successfully. "
                "No external side effects occurred."
            ),
        }