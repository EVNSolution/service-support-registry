from uuid import UUID

from django.core.management.base import BaseCommand

from supporttickets.models import SupportTicket, SupportTicketResponse

OPEN_TICKET_ID = UUID("93000000-0000-0000-0000-000000000001")
RESOLVED_TICKET_ID = UUID("93000000-0000-0000-0000-000000000002")
FIRST_RESPONSE_ID = UUID("93000000-0000-0000-0000-000000000101")
SEED_REQUESTER_ID = UUID("93000000-0000-0000-0000-000000000201")
SEED_ADMIN_ID = UUID("93000000-0000-0000-0000-000000000202")


class Command(BaseCommand):
    help = "Seed deterministic support registry bootstrap data."

    def handle(self, *args, **options):
        open_ticket, _ = SupportTicket.objects.update_or_create(
            ticket_id=OPEN_TICKET_ID,
            defaults={
                "requester_account_id": SEED_REQUESTER_ID,
                "title": "Driver App Inquiry",
                "body": "App upload failed during delivery completion.",
                "status": SupportTicket.Status.OPEN,
                "priority": SupportTicket.Priority.HIGH,
            },
        )
        SupportTicket.objects.update_or_create(
            ticket_id=RESOLVED_TICKET_ID,
            defaults={
                "requester_account_id": SEED_REQUESTER_ID,
                "title": "Settlement Inquiry",
                "body": "Settlement item review completed.",
                "status": SupportTicket.Status.RESOLVED,
                "priority": SupportTicket.Priority.MEDIUM,
            },
        )
        SupportTicketResponse.objects.update_or_create(
            response_id=FIRST_RESPONSE_ID,
            defaults={
                "ticket": open_ticket,
                "author_account_id": SEED_ADMIN_ID,
                "author_role": "admin",
                "body": "Support team is checking the upload log now.",
            },
        )
        self.stdout.write(self.style.SUCCESS("Seeded support registry bootstrap data."))
