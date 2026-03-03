from rest_framework.viewsets import ModelViewSet

from .models import Question, SurveyTemplate
from .permissions import IsHRQuestionManager, IsHRTemplateManager
from .serializers import QuestionSerializer, SurveyTemplateSerializer


class QuestionViewSet(ModelViewSet):
    queryset = Question.objects.all().order_by("id")
    serializer_class = QuestionSerializer
    permission_classes = [IsHRQuestionManager]


class SurveyTemplateViewSet(ModelViewSet):
    queryset = SurveyTemplate.objects.all().order_by("-version")
    serializer_class = SurveyTemplateSerializer
    permission_classes = [IsHRTemplateManager]
