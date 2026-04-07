import logging

try:
    from drf_spectacular.utils import extend_schema
except ModuleNotFoundError:
    def extend_schema(*args, **kwargs):
        def decorator(target):
            return target

        return decorator

from django.db.models import Q
from django.http import Http404
from rest_framework import generics, mixins, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from supporttickets.models import SupportTicket, SupportTicketResponse
from supporttickets.permissions import AuthenticatedTicketAccess, is_admin
from supporttickets.serializers import (
    HealthSerializer,
    SupportTicketResponseSerializer,
    SupportTicketSerializer,
)
from supporttickets.services.notification_handoff_service import send_support_reply_inbox_notification

logger = logging.getLogger(__name__)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: HealthSerializer})
    def get(self, request):
        return Response({"status": "ok"})


class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [AuthenticatedTicketAccess]

    def get_queryset(self):
        queryset = SupportTicket.objects.all()
        user = self.request.user

        if not is_admin(user):
            queryset = queryset.filter(requester_account_id=user.account_id)

        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        priority = self.request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        requester_account_id = self.request.query_params.get("requester_account_id")
        if requester_account_id and is_admin(user):
            queryset = queryset.filter(requester_account_id=requester_account_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(requester_account_id=self.request.user.account_id)


class TicketDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):
    serializer_class = SupportTicketSerializer
    permission_classes = [AuthenticatedTicketAccess]
    http_method_names = ["get", "patch", "options", "head"]

    def get_object(self):
        ticket_ref = self.kwargs["ticket_ref"]
        queryset = self.get_queryset()
        if ticket_ref.isdigit():
            filters = Q(route_no=int(ticket_ref))
        else:
            filters = Q(ticket_id=ticket_ref)
        ticket = queryset.filter(filters).first()
        if ticket is None:
            raise Http404
        return ticket

    def get_queryset(self):
        queryset = SupportTicket.objects.all()
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(requester_account_id=self.request.user.account_id)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Admin role required.")
        return self.partial_update(request, *args, **kwargs)


class TicketResponseListCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketResponseSerializer
    permission_classes = [AuthenticatedTicketAccess]

    def get_queryset(self):
        queryset = SupportTicketResponse.objects.select_related("ticket").all()
        user = self.request.user

        if not is_admin(user):
            queryset = queryset.filter(ticket__requester_account_id=user.account_id)

        ticket_id = self.request.query_params.get("ticket_id")
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)

        return queryset

    def perform_create(self, serializer):
        ticket = serializer.validated_data["ticket"]
        user = self.request.user

        if not is_admin(user) and str(ticket.requester_account_id) != user.account_id:
            raise PermissionDenied("Ticket owner required.")

        ticket_response = serializer.save(
            author_account_id=user.account_id,
            author_role=user.role,
        )
        if not is_admin(user) or str(ticket.requester_account_id) == user.account_id:
            return

        try:
            send_support_reply_inbox_notification(
                ticket=ticket,
                ticket_response=ticket_response,
                authorization=self.request.headers.get("Authorization", ""),
            )
        except Exception:
            logger.warning(
                "Support reply inbox handoff failed.",
                extra={
                    "ticket_id": str(ticket.ticket_id),
                    "response_id": str(ticket_response.response_id),
                    "requester_account_id": str(ticket.requester_account_id),
                },
                exc_info=True,
            )
