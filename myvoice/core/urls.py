from django.conf.urls import url
from django.core.urlresolvers import reverse_lazy

from . import views


urlpatterns = [
    url(r'^$', views.Home.as_view(), name='home'),

    # TODO - implement "Remember Me" functionality
    url(r'^accounts/login/$',
        'django.contrib.auth.views.login',
        {'template_name': 'accounts/login.html'},
        name='login'),
    url(r'^accounts/logout/$',
        'django.contrib.auth.views.logout',
        {'next_page': reverse_lazy('home')},
        name='logout'),
]
