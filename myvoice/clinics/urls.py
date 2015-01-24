from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views


urlpatterns = [
    url(r'^clinics/patient/$', views.VisitView.as_view(), name='visit'),

    url(r'^reports/region/(?P<pk>\d+)/$',
        login_required(views.LGAReport.as_view()),
        name='region_report'),
    url(r'^reports/facility/$',
        login_required(views.ClinicReportSelectClinic.as_view()),
        name='select_clinic'),
    url(r'^reports/facility/(?P<slug>[ \w-]+)/$',
        login_required(views.ClinicReport.as_view()),
        name='clinic_report'),
    url(r'^participation_analysis/$',
        views.AnalystSummary.as_view(),
        name='participation_analysis'),
    url(r'^participation_charts/$',
        views.ParticipationCharts.as_view(),
        name='participation_charts'),
    url(r'^participation_async/$',
        views.ParticipationAsync.as_view(),
        name='participation_async'),
    url(r'^wamba_report/$',
        views.LGAReport.as_view(),
        name='wamba',
        kwargs=dict(pk=599)),
    url(r'^report_filter_feedback_by_week/$',
        views.ClinicReportFilterByWeek.as_view(), name='report_filter'),
    url(r'^visit/$', views.VisitView.as_view(), name='visit'),
    url(r'^feedback/$', views.FeedbackView.as_view(), name='visit'),
    url(r'^lga_async/$', views.LGAReportAjax.as_view(), name='async_lga'),
]
