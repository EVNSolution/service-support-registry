from django.core.management import call_command
from django.test import TestCase

from supporttickets.models import SupportTicket, SupportTicketResponse


class SeedSupportCommandTests(TestCase):
    def test_seed_support_creates_expected_records_idempotently(self) -> None:
        call_command("seed_support")
        self.assertEqual(SupportTicket.objects.count(), 2)
        self.assertEqual(SupportTicketResponse.objects.count(), 1)

        call_command("seed_support")
        self.assertEqual(SupportTicket.objects.count(), 2)
        self.assertEqual(SupportTicketResponse.objects.count(), 1)
