from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^analyst_summary/$',
        views.AnalystSummary.as_view(),
        name='analyst_summary'),
]
