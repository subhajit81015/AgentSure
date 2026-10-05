from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticationResult:
    authenticated: bool
    actor: str | None
    reason: str


def authenticate_actor(
    actor: str | None,
) -> AuthenticationResult:
    """
    Basic application-level authentication boundary.

    Production identity-provider integration can be connected later.
    """

    if not actor:
        return AuthenticationResult(
            authenticated=False,
            actor=None,
            reason="Actor authentication is required.",
        )

    actor = actor.strip()

    if not actor:
        return AuthenticationResult(
            authenticated=False,
            actor=None,
            reason="Actor authentication is required.",
        )

    return AuthenticationResult(
        authenticated=True,
        actor=actor,
        reason="Actor authenticated.",
    )