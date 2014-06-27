from django.conf.urls import url


urlpatterns = [
    url(r'^$', 'myvoice.clinics.views.visit', name='visit'),
]
