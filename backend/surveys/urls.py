from rest_framework.routers import DefaultRouter

from .views import QuestionViewSet, SurveyTemplateViewSet

router = DefaultRouter()
router.register("questions", QuestionViewSet, basename="question")
router.register("survey-templates", SurveyTemplateViewSet, basename="survey-template")

urlpatterns = router.urls
