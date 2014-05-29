from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^dashboard/$', views.PBFDashboard.as_view(), name='pbf_dashboard'),
]
