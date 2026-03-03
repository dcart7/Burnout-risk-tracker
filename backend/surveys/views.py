from rest_framework.viewsets import ModelViewSet

from .models import Question
from .permissions import IsHRQuestionManager
from .serializers import QuestionSerializer


class QuestionViewSet(ModelViewSet):
    queryset = Question.objects.all().order_by("id")
    serializer_class = QuestionSerializer
    permission_classes = [IsHRQuestionManager]
