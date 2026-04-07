from django.urls import path

from supporttickets.views import HealthView, TicketDetailView, TicketListCreateView, TicketResponseListCreateView

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("tickets/", TicketListCreateView.as_view()),
    path("tickets/<str:ticket_ref>/", TicketDetailView.as_view()),
    path("ticket-responses/", TicketResponseListCreateView.as_view()),
]
