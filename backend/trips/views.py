from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import PlanTripSerializer
from .services.geocoding import geocode
from .services.hos_planner import plan_trip
from .services.routing import route_between


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "spotter-trip-planner"})


class PlanTripView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PlanTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            current = geocode(data["current_location"])
            pickup = geocode(data["pickup_location"])
            dropoff = geocode(data["dropoff_location"])
            route = route_between(
                [
                    (current["lat"], current["lon"]),
                    (pickup["lat"], pickup["lon"]),
                    (dropoff["lat"], dropoff["lon"]),
                ]
            )
            result = plan_trip(
                current=current,
                pickup=pickup,
                dropoff=dropoff,
                current_cycle_used=data["current_cycle_used"],
                route=route,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 — surface upstream API failures cleanly
            return Response(
                {"detail": f"Planning failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result)
