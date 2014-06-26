from django.contrib import admin

from . import importer
from . import models


class SurveyQuestionInline(admin.TabularInline):
    """
    Disallow adding or deleting SurveyQuestions through the admin - they must
    be managed through the automatic import of Surveys.

    Also disallow editing most of the fields that we import from TextIt.
    """

    extra = 0
    fields = ['id', 'question_id', 'question', 'label', 'question_type',
              'categories', 'designation', 'order', 'statistic', 'for_display']
    model = models.SurveyQuestion
    readonly_fields = ['id', 'question_id', 'label', 'question_type',
                       'categories']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SurveyAdmin(admin.ModelAdmin):
    """
    To add a Survey, the user should enter the flow id and let us handle
    importing the rest of the data from TextIt. After that, nothing is
    editable save some data fields on each question. If edits need to be made
    the Survey should be deleted and re-added.
    """

    add_fieldsets = [
        (None, {
            'description': "Enter the flow id and we will import its details "
                           "from TextIt.",
            'classes': ['wide'],
            'fields': ['flow_id', 'role'],
        }),
    ]
    fields = ['flow_id', 'name', 'role', 'active']
    list_display = ['name', 'flow_id', 'role', 'question_count']
    save_on_top = True

    def add_view(self, *args, **kwargs):
        self.inlines = []
        self.readonly_fields = []
        return super(SurveyAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.inlines = [SurveyQuestionInline]
        self.readonly_fields = ['flow_id', 'name']
        return super(SurveyAdmin, self).change_view(*args, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(SurveyAdmin, self).get_fieldsets(request, obj)

    def question_count(self, obj):
        return obj.surveyquestion_set.count()

    def save_model(self, request, obj, form, change):
        """If we're adding the survey, import its name and questions."""
        super(SurveyAdmin, self).save_model(request, obj, form, change)
        if not change:
            # FIXME - An exception is raised if this flow doesn't exist
            # on TextIt; instead we should check for this in form validation.
            importer.import_survey(obj.flow_id)


class SurveyQuestionResponseAdmin(admin.ModelAdmin):
    """
    Disallow adding or deleting responses through the admin - they must be
    managed through automatic import.

    Also disallow editing the fields that we import from TextIt.
    """

    fieldsets = [
        (None, {
            'fields': ['run_id', 'question'],
        }),
        ('The response', {
            'fields': ['connection', 'clinic', 'service', 'response', 'datetime'],
        }),
        ('Metadata', {
            'fields': ['created', 'updated'],
        }),
    ]
    list_display = ['run_id', 'clinic', 'service', 'survey', 'question',
                    'question_type', 'response']
    list_filter = ['question__survey', 'clinic', 'service',
                   'question__question_type']
    list_select_related = True
    ordering = ['run_id', 'question']
    readonly_fields = ['run_id', 'connection', 'question', 'response',
                       'datetime', 'created', 'updated']
    search_fields = ['response', 'run_id', 'question__label']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def question_type(self, obj):
        return obj.question.get_question_type_display()

    def survey(self, obj):
        return obj.question.survey


admin.site.register(models.Survey, SurveyAdmin)
admin.site.register(models.SurveyQuestionResponse, SurveyQuestionResponseAdmin)
