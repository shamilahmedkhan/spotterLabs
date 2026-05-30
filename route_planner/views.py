from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import RoutePlanningError
from .serializers import RoutePlanRequestSerializer
from .services.planner import RoutePlannerService


class RoutePlanView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = RoutePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        planner = RoutePlannerService()
        try:
            payload = planner.build_plan(
                start=serializer.validated_data["start"],
                finish=serializer.validated_data["finish"],
            )
        except RoutePlanningError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(payload, status=status.HTTP_200_OK)
