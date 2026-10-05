from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "operator": {
        "approval.read",
        "execution.read",
    },
    "reviewer": {
        "approval.read",
        "approval.approve",
        "approval.reject",
        "execution.read",
    },
    "admin": {
        "approval.read",
        "approval.approve",
        "approval.reject",
        "execution.read",
        "execution.execute",
    },
}


def authorize(
    role: str,
    permission: str,
) -> AuthorizationDecision:
    normalized_role = role.strip().lower()
    normalized_permission = permission.strip().lower()

    if not normalized_role:
        return AuthorizationDecision(
            allowed=False,
            reason="Role is required.",
        )

    if not normalized_permission:
        return AuthorizationDecision(
            allowed=False,
            reason="Permission is required.",
        )

    permissions = ROLE_PERMISSIONS.get(normalized_role)

    if permissions is None:
        return AuthorizationDecision(
            allowed=False,
            reason="Unknown role.",
        )

    if normalized_permission not in permissions:
        return AuthorizationDecision(
            allowed=False,
            reason=(
                f"Role '{normalized_role}' does not have "
                f"permission '{normalized_permission}'."
            ),
        )

    return AuthorizationDecision(
        allowed=True,
        reason="Permission granted.",
    )