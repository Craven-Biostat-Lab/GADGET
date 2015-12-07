from django.conf.urls import patterns, include, url

#import eventview.eventview as ev
import geneview.geneview as gv
import geneview.genecrossrefs as gxr
import abstracts.abstracts as ab
#import keyphraseview.keyphraseview as kv
import geneindex.fileupload as gfu
import metaboliteview.metaboliteview as mv


from django.conf import settings
import os

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()


GADGET_URLs = patterns('',
    (r'^genesearch', gv.searchpage),
    (r'^genelist', gv.genesearch),
    (r'^genecrossrefs', gxr.genecrossrefs),
    (r'^metabolitesearch', mv.searchpage),
    (r'^metabolitelist', mv.metabolitesearch),
    (r'^abstractview', ab.abstractview),
    (r'^abstract', ab.abstracts),
    #(r'^eventsearch', ev.search),
    #(r'^eventlist', ev.eventlist),
    #(r'^eventgenes', ev.eventgenes),
    #(r'^eventsummary', ev.eventsummary),
    #(r'^eventplot', ev.plot),
    #(r'^eventthumb', ev.thumb),
    #(r'^xml', ev.xml),
    #(r'^keywordlist', kv.keyphrasesearch),
    #(r'^keywordsearch', kv.searchpage),
    (r'^genefileupload', gfu.uploadpage),
    
    
)





urlpatterns = None

if settings.URLS_DEBUG: 
    # if in debug mode, prepend 'gadget/' stem to URL patterns.
    # (Apache does this when deployed.)
    urlpatterns = patterns('',
        ('^gadget/', include(GADGET_URLs)),
    
    # serve static files for only development
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root': os.path.join(settings.BASE_DIR, 'static')}),
    (r'^$', 'django.views.static.serve', 
        {'document_root': os.path.join(settings.BASE_DIR, 'www'), 'path':'index.html'}),    
    (r'^(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root':os.path.join(settings.BASE_DIR, 'www')}),
    )
    
    
else:
    urlpatterns = GADGET_URLs
