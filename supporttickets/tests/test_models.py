from django.core.exceptions import ValidationError
from django.test import TestCase

from supporttickets.models import SupportTicket, SupportTicketResponse


class SupportTicketModelTests(TestCase):
    def test_ticket_accepts_basic_fields(self) -> None:
        ticket = SupportTicket(
            requester_account_id="93000000-0000-0000-0000-000000000201",
            title="Driver Inquiry",
            body="Need support",
            status=SupportTicket.Status.OPEN,
            priority=SupportTicket.Priority.MEDIUM,
        )

        ticket.full_clean()

    def test_ticket_allocates_route_no(self) -> None:
        first = SupportTicket.objects.create(
            requester_account_id="93000000-0000-0000-0000-000000000201",
            title="First Inquiry",
            body="Need support",
            status=SupportTicket.Status.OPEN,
            priority=SupportTicket.Priority.MEDIUM,
        )
        second = SupportTicket.objects.create(
            requester_account_id="93000000-0000-0000-0000-000000000202",
            title="Second Inquiry",
            body="Need more support",
            status=SupportTicket.Status.OPEN,
            priority=SupportTicket.Priority.MEDIUM,
        )

        self.assertEqual(first.route_no, 1)
        self.assertEqual(second.route_no, 2)

    def test_response_rejects_closed_ticket(self) -> None:
        ticket = SupportTicket.objects.create(
            requester_account_id="93000000-0000-0000-0000-000000000201",
            title="Closed Ticket",
            body="Closed",
            status=SupportTicket.Status.CLOSED,
            priority=SupportTicket.Priority.LOW,
        )
        response = SupportTicketResponse(
            ticket=ticket,
            author_account_id="93000000-0000-0000-0000-000000000202",
            author_role="admin",
            body="Late response",
        )

        with self.assertRaises(ValidationError):
            response.full_clean()
