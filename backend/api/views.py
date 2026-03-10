from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.views import APIView
from rest_framework import status

from users.permissions import HasRBACPermissions
from analytics.services import (
    get_company_analytics,
    get_employee_dashboard,
    get_team_analytics_for_manager,
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
        dashboard = get_employee_dashboard(request.user)
        return Response(dashboard)


class ManagerAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_team_analytics",)

    def get(self, request):
        team_id = request.query_params.get("team_id")
        parsed_team_id = None
        if team_id is not None:
            try:
                parsed_team_id = int(team_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Query parameter 'team_id' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            analytics_data = get_team_analytics_for_manager(
                manager=request.user, team_id=parsed_team_id
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(analytics_data)


class HRAlertPanelView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_alert_panel",)

    def get(self, request):
        return Response({"detail": "HR alert panel access granted."})


class HRCompanyAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_company_analytics",)

    def get(self, request):
        analytics_data = get_company_analytics()
        return Response(analytics_data)


class CompanyMetricsView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.view_company_analytics",)

    def get(self, request):
        metrics = get_company_analytics()
        return Response(metrics)
