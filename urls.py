from django.conf.urls.defaults import *
import wordsearch.wordsearch as ws

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    ('^generank', ws.search),
    ('^result', ws.result),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root': '/home/genetext/genetext/static'}),
    # Example:
    # (r'^genetext/', include('genetext.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
