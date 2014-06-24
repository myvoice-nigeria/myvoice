from django.contrib import admin

from . import models


class StatisticInline(admin.TabularInline):
    extra = 0
    model = models.Statistic
    prepopulated_fields = {'slug': ['name']}


class StatisticGroupAdmin(admin.ModelAdmin):
    inlines = [StatisticInline]
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ['name']}


admin.site.register(models.StatisticGroup, StatisticGroupAdmin)
