from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    requester: str
    summary: str
    status: str
    priority: str


TICKETS = {
    "INC-10452": Ticket(
        ticket_id="INC-10452",
        requester="employee-2048",
        summary="VPN not connecting after password reset",
        status="OPEN",
        priority="P2",
    ),
    "INC-10518": Ticket(
        ticket_id="INC-10518",
        requester="employee-3117",
        summary="Outlook sign-in failure",
        status="OPEN",
        priority="P3",
    ),
}


def get_ticket(ticket_id: str) -> Ticket | None:
    return TICKETS.get(ticket_id)


def check_vpn_status() -> dict:
    return {"service": "corporate-vpn", "status": "HEALTHY", "checked_by": "serviceops-sim"}


def check_m365_status() -> dict:
    return {"service": "microsoft-365", "status": "HEALTHY", "checked_by": "serviceops-sim"}


def check_dns() -> dict:
    return {"service": "internal-dns", "status": "HEALTHY", "checked_by": "serviceops-sim"}


def update_ticket(ticket_id: str, note: str) -> dict:
    return {"ticket_id": ticket_id, "status": "UPDATED", "note": note}


def request_human_approval(ticket_id: str, action: str, reason: str) -> dict:
    return {
        "ticket_id": ticket_id,
        "action": action,
        "status": "PENDING_APPROVAL",
        "reason": reason,
    }
