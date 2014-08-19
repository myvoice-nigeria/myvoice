from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views


urlpatterns = [
    url(r'^clinics/patient/$', views.VisitView.as_view(), name='visit'),

    url(r'^reports/region/(?P<pk>\d+)/$',
        login_required(views.RegionReport.as_view()),
        name='region_report'),
    url(r'^reports/facility/$',
        login_required(views.ClinicReportSelectClinic.as_view()),
        name='select_clinic'),
    url(r'^reports/facility/(?P<slug>[ \w-]+)/$',
        login_required(views.ClinicReport.as_view()),
        name='clinic_report'),
    url(r'^visit/$', views.VisitView.as_view(), name='visit'),
    url(r'^feedback/$', views.FeedbackView.as_view(), name='visit'),
]
