from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .action_executor import (
    ActionExecutionError,
    SimulatedActionExecutor,
)
from .models import (
    ApprovalExecution,
    ApprovalRecord,
    AuditEvent,
)
from .policies.tool_policy import (
    SERVICEOPS_APPROVAL_POLICY_VERSION,
    evaluate_tool,
)


class ApprovalExecutionService:
    def __init__(self):
        self.executor = SimulatedActionExecutor()

    def _validate_approval(
        self,
        approval: ApprovalRecord,
        requested_actions: list[str],
    ) -> None:
        if approval.status != "APPROVED":
            raise ActionExecutionError(
                "Only APPROVED requests can be executed."
            )

        if (
            approval.policy_version
            != SERVICEOPS_APPROVAL_POLICY_VERSION
        ):
            raise ActionExecutionError(
                "Approval policy version is no longer current."
            )

        expires_at = approval.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        now = datetime.now(timezone.utc)

        if now >= expires_at:
            raise ActionExecutionError(
                "Approval has expired and cannot be executed."
            )

        for action in requested_actions:
            if not isinstance(action, str):
                raise ActionExecutionError(
                    "Each approved action must be a string."
                )

            policy = evaluate_tool(action)

            if not policy.allowed:
                raise ActionExecutionError(
                    f"Action is not registered by agent policy: "
                    f"{action}"
                )

            if not policy.requires_human_approval:
                raise ActionExecutionError(
                    f"Action is no longer classified as "
                    f"high-impact requiring approval: {action}"
                )

    def execute_approved(
        self,
        db: Session,
        approval: ApprovalRecord,
    ) -> dict[str, Any]:
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

        self._validate_approval(
            approval,
            requested_actions,
        )

        existing_execution = (
            db.query(ApprovalExecution)
            .filter(
                ApprovalExecution.approval_id
                == approval.approval_id,
            )
            .first()
        )

        if existing_execution is not None:
            raise ActionExecutionError(
                "Approval has already been executed"
            )

        executions = []

        for action in requested_actions:
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

        execution = ApprovalExecution(
            approval_id=approval.approval_id,
            run_id=approval.run_id,
            status="SIMULATED_SUCCESS",
            execution_mode="SIMULATED",
            completed_at=datetime.now(timezone.utc),
            result={
                "actions": executions,
                "message": (
                    "All approved actions were simulated successfully. "
                    "No external side effects occurred."
                ),
            },
        )

        audit_event = AuditEvent(
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

        db.add(execution)
        db.add(audit_event)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()

            raise ActionExecutionError(
                "Approval has already been executed"
            ) from exc

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

    def get_execution(
        self,
        db: Session,
        approval: ApprovalRecord,
    ) -> ApprovalExecution:
        execution = (
            db.query(ApprovalExecution)
            .filter(
                ApprovalExecution.approval_id
                == approval.approval_id,
            )
            .first()
        )

        if execution is None:
            raise ActionExecutionError(
                "Approval has not been executed"
            )

        return execution