from django.urls import include, path

urlpatterns = [
    path("", include("supporttickets.urls")),
]
