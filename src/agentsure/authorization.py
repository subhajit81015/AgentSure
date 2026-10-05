from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


def authorize_action(
    actor: str,
    action: str,
    risk_level: str,
) -> AuthorizationDecision:
    if not actor:
        return AuthorizationDecision(
            allowed=False,
            reason="Actor is required.",
        )

    if not action:
        return AuthorizationDecision(
            allowed=False,
            reason="Action is required.",
        )

    if risk_level not in {
        "low",
        "medium",
        "high",
        "critical",
    }:
        return AuthorizationDecision(
            allowed=False,
            reason="Invalid risk level.",
        )

    if risk_level in {"high", "critical"}:
        return AuthorizationDecision(
            allowed=False,
            reason=(
                "High-impact actions require explicit "
                "human approval."
            ),
        )

    return AuthorizationDecision(
        allowed=True,
        reason="Action authorized.",
    )
