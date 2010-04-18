from django.conf.urls.defaults import *
import settings

from django.contrib import admin
admin.autodiscover()

from booklistapp.models import Book

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^feedback', 'infxbooklist.booklistapp.views.feedback'),
    (r'^edit', 'infxbooklist.booklistapp.views.edit'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^(?P<path>favicon\.ico)$', 'django.views.static.serve',
            {'document_root': 'static'}),
        (r'^static/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': 'static'}),
        (r'^bookcovers/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': 'bookcovers'})
    )
    
urlpatterns += patterns('',
    (r'^(?P<category>.*)', 'infxbooklist.booklistapp.views.index'),
)