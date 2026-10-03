from dataclasses import dataclass

SERVICEOPS_APPROVAL_POLICY_VERSION = "serviceops-approval-v1"


@dataclass(frozen=True)
class ToolPolicy:
    allowed: bool
    requires_human_approval: bool
    reason: str


READ_ONLY_TOOLS = {
    "get_ticket",
    "search_knowledge_base",
    "check_vpn_status",
    "check_m365_status",
    "check_dns",
}

APPROVAL_TOOLS = {
    "update_ticket",
    "request_human_approval",
}

HIGH_RISK_TOOLS = {
    "reset_password",
    "disable_account",
    "delete_ticket",
    "delete_old_credentials",
}


def evaluate_tool(tool_name: str) -> ToolPolicy:
    if tool_name in READ_ONLY_TOOLS:
        return ToolPolicy(
            True,
            False,
            "Read-only diagnostic tool",
        )

    if tool_name in APPROVAL_TOOLS:
        return ToolPolicy(
            True,
            False,
            "Approved operational tool",
        )

    if tool_name in HIGH_RISK_TOOLS:
        return ToolPolicy(
            True,
            True,
            "High-impact action requires human approval",
        )

    return ToolPolicy(
        False,
        False,
        "Tool is not registered for this agent",
    )