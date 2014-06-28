from django.conf.urls import url

from .views import VisitView


urlpatterns = [
    url(r'^$', VisitView.as_view(), name='visit'),
]
