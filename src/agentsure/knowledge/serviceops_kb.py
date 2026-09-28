from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeArticle:
    article_id: str
    title: str
    keywords: tuple[str, ...]
    guidance: str
    recommended_action: str


ARTICLES = (
    KnowledgeArticle(
        article_id="KB-VPN-001",
        title="VPN authentication after password reset",
        keywords=("vpn", "password", "reset", "authentication"),
        guidance=(
            "After a password reset, cached credentials can prevent VPN authentication. "
            "Verify account status, confirm the VPN service is healthy, then reauthenticate "
            "using the updated credentials."
        ),
        recommended_action="Reauthenticate the VPN client with the updated credentials.",
    ),
    KnowledgeArticle(
        article_id="KB-OUTLOOK-001",
        title="Outlook sign-in issues",
        keywords=("outlook", "email", "signin", "login"),
        guidance=(
            "Verify Microsoft 365 account status, confirm service health, and refresh the "
            "cached credentials before escalating."
        ),
        recommended_action="Refresh cached credentials and retry Microsoft 365 sign-in.",
    ),
    KnowledgeArticle(
        article_id="KB-DNS-001",
        title="Internal application connectivity issue",
        keywords=("network", "dns", "connectivity", "internal application"),
        guidance=(
            "Check DNS resolution and endpoint reachability before escalating to the network team."
        ),
        recommended_action="Run DNS and endpoint reachability checks, then escalate with diagnostics.",
    ),
)


def search_knowledge_base(query: str) -> KnowledgeArticle | None:
    q = query.lower()
    scored: list[tuple[int, KnowledgeArticle]] = []
    for article in ARTICLES:
        score = sum(1 for keyword in article.keywords if keyword in q)
        if score:
            scored.append((score, article))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]
