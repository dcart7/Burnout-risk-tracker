from rest_framework.routers import DefaultRouter

from .views import QuestionViewSet

router = DefaultRouter()
router.register("questions", QuestionViewSet, basename="question")

urlpatterns = router.urls
