from django.conf.urls import url

from .views import VisitView


urlpatterns = [
    url(r'^visit/$', VisitView.as_view(), name='visit'),
    url(r'^feedback/$', VisitView.as_view(), name='visit'),
]
