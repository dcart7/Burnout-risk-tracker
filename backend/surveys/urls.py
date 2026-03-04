from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import QuestionViewSet, SurveyTemplateViewSet, WeeklySurveySubmissionView

router = DefaultRouter()
router.register("questions", QuestionViewSet, basename="question")
router.register("survey-templates", SurveyTemplateViewSet, basename="survey-template")

urlpatterns = [
    *router.urls,
    path("weekly-surveys/submit/", WeeklySurveySubmissionView.as_view(), name="weekly-survey-submit"),
]
