from django.conf.urls.defaults import *
import eventview.eventview as ev
import geneview.geneview as gv

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^genesearch', gv.search),
    (r'^genelist', gv.result),
    (r'^abstract', gv.abstracts),
    (r'^eventsearch', ev.search),
    (r'^eventlist', ev.eventlist),
    (r'^eventplot', ev.plot),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root': '/home/genetext/genetext/static'}),
    (r'^index', gv.front),
    (r'^$', gv.front),
    
    # Example:
    # (r'^genetext/', include('genetext.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
