from django.contrib import admin
from django.forms import BaseInlineFormSet, ValidationError

from .models import Question, SurveyTemplate, SurveyTemplateQuestion


class SurveyTemplateQuestionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        selected_questions = []
        category_counts = {
            Question.Category.STRESS: 0,
            Question.Category.WORKLOAD: 0,
            Question.Category.MOTIVATION: 0,
            Question.Category.ENERGY: 0,
        }

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            question = form.cleaned_data.get("question")
            if not question:
                continue
            selected_questions.append(question)
            category_counts[question.category] += 1

        if selected_questions and len(selected_questions) != 8:
            raise ValidationError("Template must contain exactly 8 questions.")

        invalid_categories = [
            category for category, count in category_counts.items() if count not in (0, 2)
        ]
        if invalid_categories:
            raise ValidationError("Template must contain exactly 2 questions per category.")


class SurveyTemplateQuestionInline(admin.TabularInline):
    model = SurveyTemplateQuestion
    extra = 0
    autocomplete_fields = ("question",)
    formset = SurveyTemplateQuestionInlineFormSet

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "question":
            kwargs["queryset"] = Question.objects.filter(is_active=True).order_by("id")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("text",)
    readonly_fields = ("text", "category", "is_active")

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SurveyTemplate)
class SurveyTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "version", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("version",)
    inlines = (SurveyTemplateQuestionInline,)
