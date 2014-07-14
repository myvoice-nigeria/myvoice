from django.conf.urls import url

from . import views
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^analyst_summary/$',
        TemplateView.as_view(template_name="analysts/analysts.html"),
        name='analyst_summary'),
    
]
