from django.contrib import admin

from . import models
from .forms import ClinicStatisticForm


class ClinicStaffInline(admin.TabularInline):
    model = models.ClinicStaff
    extra = 0


# NOTE: This is included for early development/debugging purposes. Eventually,
# there will be many more statistics for a clinic than a simple inline can
# handle.
class ClinicStatisticInline(admin.TabularInline):
    model = models.ClinicStatistic
    extra = 0
    form = ClinicStatisticForm


class ClinicAdmin(admin.ModelAdmin):
    inlines = [ClinicStaffInline, ClinicStatisticInline]
    list_display = ['name', 'lga']
    readonly_fields = ['lga_rank', 'pbf_rank']


class ClinicStatisticAdmin(admin.ModelAdmin):
    form = ClinicStatisticForm
    list_display = ['statistic', 'month', 'clinic', 'value', 'rank']
    readonly_fields = ['rank']


admin.site.register(models.Clinic, ClinicAdmin)
admin.site.register(models.ClinicStatistic, ClinicStatisticAdmin)
