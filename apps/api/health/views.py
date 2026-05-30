from rest_framework.response import Response
from rest_framework.views import APIView


class ServiceIndexView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "service": "tripos-api",
                "product": "TripOS",
                "admin": "/admin/",
                "health": "/api/health/",
            }
        )


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "tripos-api",
                "product": "TripOS",
            }
        )
