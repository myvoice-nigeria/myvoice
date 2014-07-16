import csv

from django.contrib import admin
from django.http import HttpResponse

from . import importer
from . import models

from myvoice.core.utils import extract_qset_data


class SurveyQuestionInline(admin.TabularInline):
    """
    Disallow adding or deleting SurveyQuestions through the admin - they must
    be managed through the automatic import of Surveys.

    Also disallow editing most of the fields that we import from TextIt.
    """

    extra = 0
    fields = ['id', 'question_id', 'question', 'label', 'question_type',
              'categories']
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
    list_display = ['name', 'flow_id', 'role', 'active']
    list_filter = ['active']
    save_on_top = True

    def add_view(self, *args, **kwargs):
        self.inlines = []
        self.readonly_fields = []
        return super(SurveyAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.inlines = [SurveyQuestionInline]
        self.readonly_fields = ['flow_id']
        return super(SurveyAdmin, self).change_view(*args, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(SurveyAdmin, self).get_fieldsets(request, obj)

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
            'fields': ['question', 'visit', 'clinic', 'service', 'response',
                       'datetime'],
        }),
        ('Metadata', {
            'fields': ['created', 'updated'],
        }),
    ]
    list_display = ['mobile', 'visit_time', 'clinic', 'service', 'survey',
                    'question', 'question_type', 'response']
    list_filter = ['question__survey', 'clinic', 'service',
                   'question__question_type']
    list_select_related = True
    ordering = ['visit', 'question']
    readonly_fields = ['question', 'response', 'datetime', 'visit', 'clinic',
                       'service', 'created', 'updated']
    search_fields = ['visit__mobile', 'response', 'question__label']
    actions = ['export_to_csv']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def visit_time(self, obj):
        return obj.visit.visit_time

    def question_type(self, obj):
        return obj.question.get_question_type_display()

    def survey(self, obj):
        return obj.question.survey

    def mobile(self, obj):
        return obj.visit.mobile

    def export_to_csv(self, request, queryset):
        headers = ['visit.mobile', 'visit.visit_time', 'clinic', 'service',
                   'question.survey', 'question', 'question.get_question_type_display',
                   'response', 'datetime', 'visit.patient.serial']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=response_data.csv'
        data = extract_qset_data(queryset, headers)
        writer = csv.writer(response)
        for line in data:
            writer.writerow(line)
        return response


admin.site.register(models.Survey, SurveyAdmin)
admin.site.register(models.SurveyQuestionResponse, SurveyQuestionResponseAdmin)
