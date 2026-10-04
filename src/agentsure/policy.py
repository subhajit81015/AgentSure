from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    level: str
    human_approval_required: bool
    release_decision: str
    reason: str


def evaluate_risk(
    *,
    critical_failure_count: int,
    approval_required: bool,
    approval_risk_level: str | None,
    arai_score: float,
) -> RiskDecision:
    if critical_failure_count > 0:
        return RiskDecision(
            level="CRITICAL",
            human_approval_required=False,
            release_decision="NO-GO",
            reason="Critical evaluation failures detected.",
        )

    if approval_required:
        level = (
            approval_risk_level.upper()
            if approval_risk_level
            else "HIGH"
        )

        return RiskDecision(
            level=level,
            human_approval_required=True,
            release_decision="CONDITIONAL GO",
            reason=(
                "High-impact action requires human approval "
                "before execution."
            ),
        )

    if arai_score < 70:
        return RiskDecision(
            level="HIGH",
            human_approval_required=True,
            release_decision="CONDITIONAL GO",
            reason="ARAI score is below the acceptable threshold.",
        )

    return RiskDecision(
        level="LOW",
        human_approval_required=False,
        release_decision="GO",
        reason="Evaluation passed without blocking conditions.",
    )