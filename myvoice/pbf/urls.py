from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^dashboard/$',
        views.PBFDashboardSelect.as_view(),
        name='pbf_dashboard_select'),
    url(r'^dashboard/(?P<clinic_slug>[\w+]+)/$',
        views.PBFDashboard.as_view(),
        name='pbf_dashboard'),
]
