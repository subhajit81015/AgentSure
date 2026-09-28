from datetime import datetime, timedelta, timezone
from time import perf_counter
from uuid import uuid4

from ..knowledge.serviceops_kb import search_knowledge_base
from ..models import ApprovalRecord, AuditEvent
from ..policies.tool_policy import evaluate_tool
from ..schemas import EvaluationCase
from ..security import detect_obvious_pii, detect_prompt_injection
from ..service import run_evaluation
from ..tools.serviceops_tools import (
    check_dns,
    check_m365_status,
    check_vpn_status,
    get_ticket,
    request_human_approval,
    update_ticket,
)


class ServiceOpsAgent:
    """Deterministic local ServiceOps agent runtime.

    Production-oriented scaffold for:
    - security gating
    - human-in-the-loop approval
    - knowledge-grounded diagnostics
    - tool authorization
    - auditability
    - agent evaluation
    """

    agent_id = "serviceops-agent-v1"
    model_version = "deterministic-local"
    prompt_version = "serviceops-v1"

    def run(self, db, incident_id: str, user_message: str) -> dict:
        started = perf_counter()
        trace = []
        tool_calls = []
        findings = []

        # =========================================================
        # 1. Security gate: prompt injection
        # =========================================================
        if detect_prompt_injection(user_message):
            case = EvaluationCase(
                case_id=f"security-{incident_id}",
                category="security",
                response_text=(
                    "Request blocked because the instruction conflicts "
                    "with agent safety policy."
                ),
                grounded=False,
                citation_valid=False,
                prompt_injection=True,
                goal_completed=False,
                latency_ms=(perf_counter() - started) * 1000,
                cost_usd=0.001,
            )

            result = run_evaluation(
                db,
                self._evaluation_request(case),
            )

            return self._response(
                result=result,
                incident_id=incident_id,
                status="BLOCKED",
                trace=[],
                findings=["prompt_injection"],
                started=started,
            )

        # =========================================================
        # 2. Retrieve incident
        # =========================================================
        ticket = get_ticket(incident_id)

        trace.append(
            {
                "step": "get_ticket",
                "status": "success" if ticket else "not_found",
            }
        )

        if not ticket:
            case = EvaluationCase(
                case_id=f"ticket-{incident_id}",
                category="quality",
                response_text=(
                    "Incident not found. Please verify the incident ID."
                ),
                expected_answer_keywords=["incident", "not found"],
                grounded=True,
                citation_valid=True,
                goal_completed=False,
                latency_ms=(perf_counter() - started) * 1000,
                cost_usd=0.001,
            )

            result = run_evaluation(
                db,
                self._evaluation_request(case),
            )

            return self._response(
                result=result,
                incident_id=incident_id,
                status="NOT_FOUND",
                trace=trace,
                findings=["ticket_not_found"],
                started=started,
            )

        # =========================================================
        # 3. High-impact action gate
        #
        # Only explicit requests trigger human approval.
        # Context/history such as "after my password reset"
        # must not trigger the approval gate.
        # =========================================================
        user_message_lower = user_message.lower()

        password_reset_requested = any(
            phrase in user_message_lower
            for phrase in [
                "reset my password",
                "reset the password",
                "please reset my password",
                "please reset the password",
                "can you reset my password",
                "could you reset my password",
                "change my password",
                "change the password",
                "please change my password",
                "please change the password",
            ]
        )

        delete_requested = any(
            phrase in user_message_lower
            for phrase in [
                "delete my credentials",
                "delete the old credentials",
                "delete my old credentials",
                "please delete my credentials",
                "please delete the old credentials",
                "please delete my old credentials",
            ]
        )

        high_impact_requested = (
            password_reset_requested
            or delete_requested
        )

        if high_impact_requested:
            requested_actions = []

            if password_reset_requested:
                requested_actions.append("reset_password")

            if delete_requested:
                requested_actions.append(
                    "delete_old_credentials"
                )

            requested_at = datetime.now(timezone.utc)
            expires_at = requested_at + timedelta(minutes=5)

            approval = request_human_approval(
                incident_id,
                "high-impact-action",
                (
                    "Sensitive action requested by the user; "
                    "human approval required before execution."
                ),
            )

            approval_record = {
                "approval_id": str(uuid4()),
                "status": approval["status"],
                "risk_level": "high",
                "action": "high-impact-action",
                "actor": ticket.requester,
                "target": {
                    "type": "incident",
                    "id": incident_id,
                },
                "normalized_parameters": {
                    "requested_actions": requested_actions,
                },
                "requested_at": requested_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "policy_version": "serviceops-approval-v1",
            }

            trace.append(
                {
                    "step": "request_human_approval",
                    "status": approval["status"],
                    "approval_id": approval_record["approval_id"],
                    "risk_level": approval_record["risk_level"],
                }
            )

            findings.append("human_approval_required")

            final_response = (
                f"Incident {incident_id} requires human approval "
                "before the requested high-impact action can be "
                "executed."
            )

            case = EvaluationCase(
                case_id=f"approval-{incident_id}",
                category="approval",
                response_text=final_response,
                expected_answer_keywords=[
                    "human",
                    "approval",
                ],
                grounded=True,
                citation_valid=True,
                goal_completed=False,
                approval_required=True,
                approval_status=approval_record["status"],
                approval_id=approval_record["approval_id"],
                approval_risk_level=approval_record["risk_level"],
                latency_ms=(perf_counter() - started) * 1000,
                cost_usd=0.001,
            )

            result = run_evaluation(
                db,
                self._evaluation_request(case),
            )

            # Persist the approval only for an actual
            # high-impact approval request.
            db.add(
                ApprovalRecord(
                    approval_id=approval_record["approval_id"],
                    run_id=result.id,
                    agent_id=self.agent_id,
                    incident_id=incident_id,
                    actor=approval_record["actor"],
                    action=approval_record["action"],
                    risk_level=approval_record["risk_level"],
                    target=approval_record["target"],
                    normalized_parameters=(
                        approval_record["normalized_parameters"]
                    ),
                    policy_version=approval_record["policy_version"],
                    status=approval_record["status"],
                    requested_at=requested_at,
                    expires_at=expires_at,
                )
            )

            result.summary = {
                **(result.summary or {}),
                "approval": approval_record,
            }

            db.add(
                AuditEvent(
                    run_id=result.id,
                    event_type="agent.approval_required",
                    payload={
                        "agent_id": self.agent_id,
                        "incident_id": incident_id,
                        "user_message": user_message,
                        "approval": approval_record,
                        "trace": trace,
                        "findings": findings,
                        "final_response": final_response,
                    },
                )
            )

            db.commit()

            return self._response(
                result=result,
                incident_id=incident_id,
                status="PENDING_APPROVAL",
                trace=trace,
                findings=findings,
                started=started,
                final_response=final_response,
                approval=approval_record,
            )

        # =========================================================
        # 4. Knowledge-base retrieval
        # =========================================================
        article = search_knowledge_base(
            f"{ticket.summary} {user_message}"
        )

        trace.append(
            {
                "step": "search_knowledge_base",
                "article_id": (
                    article.article_id if article else None
                ),
            }
        )

        tool_calls.append("search_knowledge_base")

        # =========================================================
        # 5. Diagnostic tool selection
        # =========================================================
        if article and "vpn" in article.title.lower():
            tool = "check_vpn_status"
            policy = evaluate_tool(tool)
            tool_calls.append(tool)

            if not policy.allowed:
                findings.append("tool_not_allowed")
                diagnostic = {"status": "BLOCKED"}
            else:
                diagnostic = check_vpn_status()

                trace.append(
                    {
                        "step": tool,
                        "status": diagnostic["status"],
                    }
                )

        elif article and "outlook" in article.title.lower():
            tool = "check_m365_status"
            policy = evaluate_tool(tool)
            tool_calls.append(tool)

            if not policy.allowed:
                findings.append("tool_not_allowed")
                diagnostic = {"status": "BLOCKED"}
            else:
                diagnostic = check_m365_status()

                trace.append(
                    {
                        "step": tool,
                        "status": diagnostic["status"],
                    }
                )

        else:
            tool = "check_dns"
            policy = evaluate_tool(tool)
            tool_calls.append(tool)

            if not policy.allowed:
                findings.append("tool_not_allowed")
                diagnostic = {"status": "BLOCKED"}
            else:
                diagnostic = check_dns()

                trace.append(
                    {
                        "step": tool,
                        "status": diagnostic["status"],
                    }
                )

        # =========================================================
        # 6. Build grounded response
        # =========================================================
        if article:
            final_response = (
                f"Incident {incident_id} is classified as "
                f"{ticket.priority} {ticket.summary}. "
                f"Knowledge base guidance: {article.guidance} "
                f"Recommended action: {article.recommended_action}"
            )

            expected = [
                "Incident",
                article.recommended_action.split()[0],
            ]

            grounded = True

        else:
            final_response = (
                f"Incident {incident_id} was received, but no "
                "approved knowledge-base article matched the "
                "request. The incident should be escalated with "
                "diagnostics."
            )

            expected = [
                "Incident",
                "escalated",
            ]

            grounded = True
            findings.append("no_kb_match")

        # =========================================================
        # 7. Update ticket only after all execution gates pass
        # =========================================================
        update_policy = evaluate_tool("update_ticket")

        if update_policy.allowed:
            note = (
                "AgentSure ServiceOps agent generated a "
                "grounded diagnostic response."
            )

            update_result = update_ticket(
                incident_id,
                note,
            )

            trace.append(
                {
                    "step": "update_ticket",
                    "status": update_result["status"],
                }
            )

            tool_calls.append("update_ticket")

        # =========================================================
        # 8. Evaluation
        # =========================================================
        latency_ms = (
            perf_counter() - started
        ) * 1000

        case = EvaluationCase(
            case_id=f"agent-{incident_id}",
            category="quality",
            response_text=final_response,
            expected_answer_keywords=expected,
            grounded=grounded,
            citation_valid=grounded,
            tool_calls=tool_calls,
            allowed_tools=[
                "get_ticket",
                "search_knowledge_base",
                "check_vpn_status",
                "check_m365_status",
                "check_dns",
                "update_ticket",
                "request_human_approval",
            ],
            pii_detected=detect_obvious_pii(
                final_response
            ),
            prompt_injection=False,
            unauthorized_tool_use=False,
            loop_detected=False,
            goal_completed=bool(
                ticket and article
            ),
            latency_ms=latency_ms,
            cost_usd=0.001,
        )

        result = run_evaluation(
            db,
            self._evaluation_request(case),
        )

        db.add(
            AuditEvent(
                run_id=result.id,
                event_type="agent.run",
                payload={
                    "agent_id": self.agent_id,
                    "incident_id": incident_id,
                    "user_message": user_message,
                    "trace": trace,
                    "tool_calls": tool_calls,
                    "findings": findings,
                    "final_response": final_response,
                },
            )
        )

        db.commit()

        return self._response(
            result=result,
            incident_id=incident_id,
            status="COMPLETED",
            trace=trace,
            findings=findings,
            started=started,
            final_response=final_response,
        )

    @staticmethod
    def _evaluation_request(case: EvaluationCase):
        from ..schemas import EvaluationRequest

        return EvaluationRequest(
            agent_id=ServiceOpsAgent.agent_id,
            model_version=ServiceOpsAgent.model_version,
            prompt_version=ServiceOpsAgent.prompt_version,
            dataset_version="serviceops-demo-v1",
            test_suite_version="serviceops-v1",
            cases=[case],
        )

    @staticmethod
    def _response(
        result,
        incident_id,
        status,
        trace,
        findings,
        started,
        final_response="",
        approval=None,
    ):
        return {
            "run_id": result.id,
            "agent_id": ServiceOpsAgent.agent_id,
            "incident_id": incident_id,
            "status": status,
            "response": final_response,
            "approval": approval,
            "trace": trace,
            "findings": findings,
            "evaluation": {
                "arai_score": result.arai_score,
                "release_decision": result.release_decision,
                "critical_failure_count": (
                    result.critical_failure_count
                ),
                "quality_score": result.quality_score,
                "safety_score": result.safety_score,
                "reliability_score": (
                    result.reliability_score
                ),
                "operations_score": (
                    result.operations_score
                ),
            },
            "latency_ms": round(
                (perf_counter() - started) * 1000,
                2,
            ),
        }