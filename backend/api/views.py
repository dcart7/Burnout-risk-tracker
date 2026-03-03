from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.views import APIView

from users.permissions import HasRBACPermissions

@api_view(['GET'])
def hello_world(request):
    return Response({"message": "Hello from Django!"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(
        {
            "id": request.user.id,
            "username": request.user.username,
            "role": getattr(request.user, "role", None),
        }
    )


class EmployeeDashboardView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_own_dashboard",)

    def get(self, request):
        return Response({"detail": "Employee dashboard access granted."})


class ManagerAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_team_analytics",)

    def get(self, request):
        return Response({"detail": "Manager analytics access granted."})


class HRAlertPanelView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_alert_panel",)

    def get(self, request):
        return Response({"detail": "HR alert panel access granted."})
