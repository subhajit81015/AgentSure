import re

PII_PATTERNS = [
    re.compile(r"\b\d{12}\b"),  # generic numeric identifier placeholder, not a production Aadhaar validator
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
]


def detect_obvious_pii(text: str) -> bool:
    return any(p.search(text) for p in PII_PATTERNS)


def detect_prompt_injection(text: str) -> bool:
    patterns = [
        "ignore previous instructions",
        "system prompt",
        "reveal hidden instructions",
        "developer message",
    ]
    normalized = text.lower()
    return any(p in normalized for p in patterns)
