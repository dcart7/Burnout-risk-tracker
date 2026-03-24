from django.urls import path
from .views import (
    EmployeeDashboardView,
    HRCompanyAnalyticsView,
    HRAlertPanelView,
    CompanyMetricsView,
    ManagerAnalyticsView,
    hello_world,
    health,
    me,
)

urlpatterns = [
    path('hello/', hello_world, name='hello_world'),
    path('health/', health, name='health'),
    path('me/', me, name='me'),
    path('rbac/employee/dashboard/', EmployeeDashboardView.as_view(), name='employee_dashboard'),
    path('rbac/manager/analytics/', ManagerAnalyticsView.as_view(), name='manager_analytics'),
    path('rbac/hr/company-analytics/', HRCompanyAnalyticsView.as_view(), name='hr_company_analytics'),
    path('rbac/hr/company-metrics/', CompanyMetricsView.as_view(), name='company_metrics'),
    path('rbac/hr/alerts/', HRAlertPanelView.as_view(), name='hr_alerts'),
]
