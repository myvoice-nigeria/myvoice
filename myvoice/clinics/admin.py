import csv

from django.contrib import admin
from django.http import HttpResponse
from leaflet.admin import LeafletGeoAdmin

from . import models

from myvoice.core.utils import extract_qset_data


class ClinicStaffInline(admin.TabularInline):
    model = models.ClinicStaff
    extra = 0
    readonly_fields = ['created', 'updated']


class ClinicAdmin(LeafletGeoAdmin):
    display_raw = True
    inlines = [ClinicStaffInline]
    list_display = ['name', 'lga', 'code']
    ordering = ['name']
    prepopulated_fields = {'slug': ['name']}
    readonly_fields = ['lga_rank', 'pbf_rank', 'created', 'updated']


class RegionAdmin(LeafletGeoAdmin):
    list_display = ['name', 'alternate_name', 'type']
    list_filter = ['type']
    ordering = ['type', 'name']
    search_fields = ['name', 'alternate_name', 'external_id']


class PatientAdmin(admin.ModelAdmin):
    list_display = ['serial', 'clinic', 'mobile']
    list_filter = ['clinic']
    list_select_related = True
    order_by = ['mobile']
    search_fields = ['name', 'mobile', 'serial']


class VisitAdmin(admin.ModelAdmin):
    date_hierarchy = 'visit_time'
    list_display = ['patient_serial', 'mobile', 'clinic', 'service',
                    'visit_time', 'welcome_sent', 'survey_sent']
    list_filter = ['patient__clinic', 'service']
    list_select_related = True
    actions = ['export_to_csv']

    def clinic(self, obj):
        return obj.patient.clinic

    def patient_serial(self, obj):
        return obj.patient.serial

    def export_to_csv(self, request, queryset):
        headers = ['patient', 'service', 'staff',
                   'visit_time', 'welcome_sent', 'survey_sent', 'mobile']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=visit_data.csv'
        data = extract_qset_data(queryset, headers)
        writer = csv.writer(response)
        for line in data:
            writer.writerow(line)
        return response


class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'code']
    ordering = ['name']


class GenericFeedbackAdmin(admin.ModelAdmin):
    list_display = ['sender', 'clinic', 'message', 'message_date']


admin.site.register(models.Clinic, ClinicAdmin)
admin.site.register(models.Region, RegionAdmin)
admin.site.register(models.Patient, PatientAdmin)
admin.site.register(models.Visit, VisitAdmin)
admin.site.register(models.Service, ServiceAdmin)
admin.site.register(models.GenericFeedback, GenericFeedbackAdmin)
