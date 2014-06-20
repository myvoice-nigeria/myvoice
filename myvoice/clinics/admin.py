from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin

from . import models
from .forms import ClinicStatisticAdminForm


class ClinicStaffInline(admin.TabularInline):
    model = models.ClinicStaff
    extra = 0


# NOTE: This is included for early development/debugging purposes. Eventually,
# there will be many more statistics for a clinic than a simple inline can
# handle.
class ClinicStatisticInline(admin.TabularInline):
    model = models.ClinicStatistic
    extra = 0
    form = ClinicStatisticAdminForm


class ClinicAdmin(admin.ModelAdmin):
    inlines = [ClinicStaffInline, ClinicStatisticInline]
    list_display = ['name', 'lga']
    prepopulated_fields = {'slug': ['name']}
    readonly_fields = ['lga_rank', 'pbf_rank']


class ClinicStatisticAdmin(admin.ModelAdmin):
    form = ClinicStatisticAdminForm
    list_display = ['statistic', 'month', 'clinic', 'value', 'rank']
    readonly_fields = ['rank']


class RegionAdmin(LeafletGeoAdmin):
    search_fields = ['name', 'alternate_name', 'external_id']
    list_display = ['name', 'alternate_name', 'type']
    list_filter = ['type']
    ordering = ['type', 'name']


admin.site.register(models.Clinic, ClinicAdmin)
admin.site.register(models.ClinicStatistic, ClinicStatisticAdmin)
admin.site.register(models.Region, RegionAdmin)
