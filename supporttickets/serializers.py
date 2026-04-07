from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from supporttickets.models import SupportTicket, SupportTicketResponse

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class SupportTicketSerializer(serializers.ModelSerializer):
    requester_account_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    updated_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)

    class Meta:
        model = SupportTicket
        fields = (
            "ticket_id",
            "route_no",
            "requester_account_id",
            "title",
            "body",
            "status",
            "priority",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("ticket_id", "route_no", "requester_account_id", "created_at", "updated_at")

    def validate(self, attrs):
        candidate = self.instance or SupportTicket()
        for field, value in attrs.items():
            setattr(candidate, field, value)
        request = self.context.get("request")
        if request is not None and getattr(request.user, "account_id", None):
            candidate.requester_account_id = request.user.account_id
        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class SupportTicketResponseSerializer(serializers.ModelSerializer):
    ticket_id = serializers.PrimaryKeyRelatedField(queryset=SupportTicket.objects.all(), source="ticket")
    author_account_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    updated_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)

    class Meta:
        model = SupportTicketResponse
        fields = (
            "response_id",
            "ticket_id",
            "author_account_id",
            "author_role",
            "body",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("response_id", "author_account_id", "author_role", "created_at", "updated_at")

    def validate(self, attrs):
        candidate = self.instance or SupportTicketResponse()
        for field, value in attrs.items():
            setattr(candidate, field, value)
        request = self.context.get("request")
        if request is not None and getattr(request.user, "account_id", None):
            candidate.author_account_id = request.user.account_id
            candidate.author_role = request.user.role
        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
