import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class NotificationHandoffError(Exception):
    """Raised when notification-hub handoff fails."""


def send_support_reply_inbox_notification(*, ticket, ticket_response, authorization: str) -> None:
    payload = {
        "recipient_account_id": str(ticket.requester_account_id),
        "category": "support",
        "source_type": "support_ticket",
        "source_ref": str(ticket.route_no),
        "title": f"[문의 #{ticket.route_no}] {ticket.title}",
        "body": ticket_response.body,
        "status": "unread",
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if authorization:
        headers["Authorization"] = authorization

    request = Request(
        f"{settings.NOTIFICATION_HUB_BASE_URL.rstrip('/')}/general/",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            response.read()
    except HTTPError as exc:
        raise NotificationHandoffError("Notification hub rejected support reply inbox handoff.") from exc
    except URLError as exc:
        raise NotificationHandoffError("Notification hub is unavailable for support reply inbox handoff.") from exc
