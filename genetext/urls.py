from django.conf.urls.defaults import *
import eventview.eventview as ev
import geneview.geneview as gv

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^gadget/genesearch', gv.search),
    (r'^gadget/genelist', gv.result),
    (r'^gadget/abstract', gv.abstracts),
    (r'^gadget/eventsearch', ev.search),
    (r'^gadget/eventlist', ev.eventlist),
    (r'^gadget/eventgenes', ev.eventgenes),
    (r'^gadget/eventplot', ev.plot),
    (r'^gadget/eventthumb', ev.thumb),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root': '/home/matt/work/gadget/static'}),
    (r'^$', 'django.views.static.serve', 
        {'document_root': '/home/matt/work/gadget/www', 'path':'index.html'}),    
    (r'^(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root': '/home/matt/work/gadget/www'}),
    
    # Example:
    # (r'^genetext/', include('genetext.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
