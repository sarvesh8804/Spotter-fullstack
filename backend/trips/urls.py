from django.urls import path

from .views import HealthView, PlanTripView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("plan-trip/", PlanTripView.as_view(), name="plan-trip"),
]
