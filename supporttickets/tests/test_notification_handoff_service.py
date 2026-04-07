import json
from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase, override_settings

from supporttickets.models import SupportTicket, SupportTicketResponse
from supporttickets.services.notification_handoff_service import send_support_reply_inbox_notification


def fake_response(body: str = "{}"):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return body.encode("utf-8")

    return FakeResponse()


class NotificationHandoffServiceTests(TestCase):
    @override_settings(NOTIFICATION_HUB_BASE_URL="http://notification-hub-api:8000")
    @patch("supporttickets.services.notification_handoff_service.urlopen")
    def test_support_reply_handoff_posts_inbox_payload(self, mock_urlopen):
        ticket = SupportTicket.objects.create(
            requester_account_id=uuid4(),
            title="Delivery issue",
            body="Need support",
            status=SupportTicket.Status.OPEN,
            priority=SupportTicket.Priority.MEDIUM,
        )
        ticket_response = SupportTicketResponse.objects.create(
            ticket=ticket,
            author_account_id=uuid4(),
            author_role="admin",
            body="We updated the route.",
        )
        mock_urlopen.return_value = fake_response()

        send_support_reply_inbox_notification(
            ticket=ticket,
            ticket_response=ticket_response,
            authorization="Bearer token",
        )

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://notification-hub-api:8000/general/")
        self.assertEqual(request.headers["Authorization"], "Bearer token")
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(request.get_method(), "POST")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["recipient_account_id"], str(ticket.requester_account_id))
        self.assertEqual(payload["category"], "support")
        self.assertEqual(payload["source_type"], "support_ticket")
        self.assertEqual(payload["source_ref"], str(ticket.route_no))
        self.assertEqual(payload["title"], f"[문의 #{ticket.route_no}] Delivery issue")
        self.assertEqual(payload["body"], "We updated the route.")
        self.assertEqual(payload["status"], "unread")
