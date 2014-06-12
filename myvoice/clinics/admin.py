from django.contrib import admin

from . import models


class ClinicStaffInline(admin.TabularInline):
    model = models.ClinicStaff
    extra = 0


class ClinicAdmin(admin.ModelAdmin):
    inlines = [ClinicStaffInline]
    list_display = ['name', 'lga']
    readonly_fields = ['lga_rank', 'pbf_rank']


class ClinicStatisticAdmin(admin.ModelAdmin):
    list_display = ['statistic', 'month', 'clinic', 'value', 'rank']
    readonly_fields = ['rank']


admin.site.register(models.Clinic, ClinicAdmin)
admin.site.register(models.ClinicStatistic, ClinicStatisticAdmin)
