import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Max


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "open"
        IN_PROGRESS = "in_progress", "in_progress"
        RESOLVED = "resolved", "resolved"
        CLOSED = "closed", "closed"

    class Priority(models.TextChoices):
        LOW = "low", "low"
        MEDIUM = "medium", "medium"
        HIGH = "high", "high"

    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route_no = models.PositiveIntegerField(unique=True, editable=False)
    requester_account_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices)
    priority = models.CharField(max_length=32, choices=Priority.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "ticket_id")

    def save(self, *args, **kwargs):
        if self.route_no is not None:
            return super().save(*args, **kwargs)

        for _ in range(5):
            self.route_no = (type(self).objects.aggregate(max_route_no=Max("route_no"))["max_route_no"] or 0) + 1
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.route_no = None

        raise IntegrityError("Failed to allocate support ticket route_no.")


class SupportTicketResponse(models.Model):
    response_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    author_account_id = models.UUIDField()
    author_role = models.CharField(max_length=32)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "response_id")

    def clean(self):
        errors = {}
        if self.ticket_id and self.ticket.status == SupportTicket.Status.CLOSED:
            errors["ticket"] = ["response cannot be added to a closed ticket."]
        if errors:
            raise ValidationError(errors)
