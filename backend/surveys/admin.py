from django.contrib import admin

from .models import Question, SurveyTemplate, SurveyTemplateQuestion


class SurveyTemplateQuestionInline(admin.TabularInline):
    model = SurveyTemplateQuestion
    extra = 0
    autocomplete_fields = ("question",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("text",)


@admin.register(SurveyTemplate)
class SurveyTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "version", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("version",)
    inlines = (SurveyTemplateQuestionInline,)
