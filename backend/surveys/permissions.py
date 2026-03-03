from rest_framework.permissions import BasePermission


class IsHRQuestionManager(BasePermission):
    message = "Only HR can manage questions."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.has_perm("users.manage_question_bank")
        )


class IsHRTemplateManager(BasePermission):
    message = "Only HR can manage survey templates."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.has_perm("users.manage_survey_templates")
        )
