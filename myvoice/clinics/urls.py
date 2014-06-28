from django.conf.urls import url

from .views import VisitView


urlpatterns = [
    url(r'^patient/$', VisitView.as_view(), name='visit'),
]
