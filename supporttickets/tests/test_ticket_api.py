from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from supporttickets.models import SupportTicket, SupportTicketResponse


class SupportTicketApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_account_id = str(uuid4())
        self.user_account_id = str(uuid4())
        self.other_account_id = str(uuid4())
        self.admin_token = self._issue_token("admin", self.admin_account_id)
        self.user_token = self._issue_token("user", self.user_account_id)
        self.other_user_token = self._issue_token("user", self.other_account_id)

    def _issue_token(self, role: str, account_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": account_id,
            "email": f"{role}@example.com",
            "role": role,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "jti": str(uuid4()),
            "type": "access",
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _authenticate(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _ticket_payload(self, *, title: str = "Driver Inquiry", priority: str = "medium"):
        return {
            "title": title,
            "body": "Need support",
            "status": "open",
            "priority": priority,
        }

    def _response_payload(self, *, ticket_id: str):
        return {
            "ticket_id": ticket_id,
            "body": "Checking now.",
        }

    def _create_ticket(self, *, requester_account_id: str, status: str = SupportTicket.Status.OPEN) -> SupportTicket:
        return SupportTicket.objects.create(
            requester_account_id=requester_account_id,
            title="Seed Ticket",
            body="Seed body",
            status=status,
            priority=SupportTicket.Priority.MEDIUM,
        )

    def test_health_endpoint_responds_publicly(self) -> None:
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    def test_unauthenticated_ticket_list_returns_401_shape(self) -> None:
        response = self.client.get("/tickets/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})

    def test_user_can_create_ticket_and_only_see_own_tickets(self) -> None:
        self._create_ticket(requester_account_id=self.other_account_id)
        self._authenticate(self.user_token)

        create_response = self.client.post("/tickets/", self._ticket_payload(), format="json")
        list_response = self.client.get("/tickets/")

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["requester_account_id"], self.user_account_id)
        self.assertIn("route_no", create_response.data)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["requester_account_id"], self.user_account_id)

    def test_user_cannot_patch_ticket(self) -> None:
        ticket = self._create_ticket(requester_account_id=self.user_account_id)
        self._authenticate(self.user_token)

        response = self.client.patch(
            f"/tickets/{ticket.ticket_id}/",
            {"status": "resolved"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_all_and_patch_ticket_status(self) -> None:
        ticket = self._create_ticket(requester_account_id=self.user_account_id)
        self._authenticate(self.admin_token)

        list_response = self.client.get("/tickets/")
        patch_response = self.client.patch(
            f"/tickets/{ticket.ticket_id}/",
            {"status": "resolved"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["status"], "resolved")

    def test_ticket_detail_accepts_route_no_lookup(self) -> None:
        self._authenticate(self.user_token)
        create_response = self.client.post("/tickets/", self._ticket_payload(), format="json")

        route_no = create_response.data["route_no"]
        detail_response = self.client.get(f"/tickets/{route_no}/")

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["route_no"], route_no)

    def test_ticket_list_filters_by_status_priority_and_requester(self) -> None:
        own_ticket = self._create_ticket(requester_account_id=self.user_account_id, status=SupportTicket.Status.OPEN)
        other_ticket = SupportTicket.objects.create(
            requester_account_id=self.other_account_id,
            title="Other",
            body="Body",
            status=SupportTicket.Status.RESOLVED,
            priority=SupportTicket.Priority.HIGH,
        )
        self._authenticate(self.admin_token)

        by_status = self.client.get("/tickets/", {"status": "resolved"})
        by_priority = self.client.get("/tickets/", {"priority": "high"})
        by_requester = self.client.get("/tickets/", {"requester_account_id": self.user_account_id})

        self.assertEqual(by_status.data[0]["ticket_id"], str(other_ticket.ticket_id))
        self.assertEqual(by_priority.data[0]["ticket_id"], str(other_ticket.ticket_id))
        self.assertEqual(by_requester.data[0]["ticket_id"], str(own_ticket.ticket_id))

    def test_owner_can_create_and_list_ticket_response(self) -> None:
        ticket = self._create_ticket(requester_account_id=self.user_account_id)
        self._authenticate(self.user_token)

        with patch("supporttickets.views.send_support_reply_inbox_notification", create=True) as mock_handoff:
            create_response = self.client.post(
                "/ticket-responses/",
                self._response_payload(ticket_id=str(ticket.ticket_id)),
                format="json",
            )
        list_response = self.client.get("/ticket-responses/", {"ticket_id": str(ticket.ticket_id)})

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["author_account_id"], self.user_account_id)
        self.assertEqual(len(list_response.data), 1)
        mock_handoff.assert_not_called()

    def test_admin_reply_creates_inbox_notification_handoff(self) -> None:
        ticket = self._create_ticket(requester_account_id=self.user_account_id)
        self._authenticate(self.admin_token)

        with patch("supporttickets.views.send_support_reply_inbox_notification", create=True) as mock_handoff:
            response = self.client.post(
                "/ticket-responses/",
                self._response_payload(ticket_id=str(ticket.ticket_id)),
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        mock_handoff.assert_called_once()
        call_kwargs = mock_handoff.call_args.kwargs
        self.assertEqual(call_kwargs["ticket"].ticket_id, ticket.ticket_id)
        self.assertEqual(call_kwargs["ticket_response"].body, "Checking now.")
        self.assertEqual(call_kwargs["authorization"], f"Bearer {self.admin_token}")

    def test_admin_reply_still_succeeds_when_notification_handoff_fails(self) -> None:
        ticket = self._create_ticket(requester_account_id=self.user_account_id)
        self._authenticate(self.admin_token)

        with patch(
            "supporttickets.views.send_support_reply_inbox_notification",
            side_effect=RuntimeError("notification hub down"),
            create=True,
        ) as mock_handoff:
            response = self.client.post(
                "/ticket-responses/",
                self._response_payload(ticket_id=str(ticket.ticket_id)),
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SupportTicketResponse.objects.count(), 1)
        mock_handoff.assert_called_once()

    def test_non_owner_cannot_create_response(self) -> None:
        ticket = self._create_ticket(requester_account_id=self.user_account_id)
        self._authenticate(self.other_user_token)

        response = self.client.post(
            "/ticket-responses/",
            self._response_payload(ticket_id=str(ticket.ticket_id)),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_closed_ticket_rejects_response(self) -> None:
        ticket = self._create_ticket(
            requester_account_id=self.user_account_id,
            status=SupportTicket.Status.CLOSED,
        )
        self._authenticate(self.admin_token)

        response = self.client.post(
            "/ticket-responses/",
            self._response_payload(ticket_id=str(ticket.ticket_id)),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("ticket", response.data["details"])
