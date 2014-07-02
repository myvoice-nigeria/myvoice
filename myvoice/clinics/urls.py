from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^clinics/patient/$', views.VisitView.as_view(), name='visit'),
    url(r'^reports/facility/(?P<slug>[ \w-]+)/$',
        views.ClinicReport.as_view(),
        name='clinic_report'),
]
