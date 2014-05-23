from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^broadcast/', include('broadcast.urls')),
    url(r'^groups/', include('groups.urls')),
    url(r'^decisiontree/', include('decisiontree.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
