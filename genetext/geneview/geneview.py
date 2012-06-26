#!/usr/bin/python
from urllib import quote
import json

from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.db.models import Sum, Count
from django import forms

import rpy2.robjects as robjects

from genetext.geneview.models import Gene, GeneAbstract, Abstract
from genetext.abstracts.index import get_abstracts, corpus_size

# allowable species (specieschoices should be in order, with the default first)
speciesnames = {'9606': 'Homo sapiens', '10090': 'Mus musculus', '559292': 'Saccharomyces cerevisiae'}
specieschoices = (('9606', 'Homo sapiens'),('10090', 'Mus musculus'), ('559292', 'Saccharomyces cerevisiae'))

def searchpage(request):
    """The search page for the word view (makes the forms)"""
    
    class SearchForm(forms.Form):
        q = forms.CharField(label='Keywords')
        genes = forms.CharField(label='Gene symbols')
        species = forms.ChoiceField(label='Species', choices=specieschoices, initial='9606')
        usehomologs = forms.BooleanField(label='Use homologs', widget=forms.CheckboxInput(check_test=parseboolean))
    
    form = SearchForm(request.GET)
    
    # get form arguments from the query string
    q = request.GET.get('q', default='')
    genes_input = request.GET.get('genes', default='')
    species = request.GET.get('species', default='9606')
    usehomologs_input = request.GET.get('usehomologs', default='')
    orderby = request.GET.get('orderby', default='f1_score')
    
    # validate species and look up name    
    if species in speciesnames:
        speciesname = speciesnames[species]
    else:
        species = '9606'
        speciesname = 'Homo sapiens'
    
    # look up gene Entrez ID's and symbols
    if genes_input:
        try:
            genes = gene_lookup(genes_input, species)
        except KeyError as (e,):
            # we couldn't find a gene symbol
            return render_to_response('genesearch.html', {'form': form, 'errormsg': 'No genes match "{0}" for {1}'.format(e, speciesname)})
        
        genesyms = [g.symbol for g in Gene.objects.filter(entrez_id__in=genes)]
    else:
        genes = ''
        genesyms = ''
    
    usehomologs = parseboolean(usehomologs_input)
    
    return render_to_response('genesearch.html', {'form': form, 'q': q, 
        'genes': map(str, genes), 'genesyms': genesyms, 'species': species, 'speciesname': speciesname,
        'usehomologs': usehomologs, 'orderby': orderby})


def gene_lookup(genes_input, species=None):
    """Given a list of gene Entrez ID's and symbols (as a comma-separated
     string), return a list of Entrez ID's"""
    
    if genes_input is None:
        return None
    
    genes = []
    for i in genes_input.split(','):
        g = i.strip()
        
        if g == '':
            continue
        
        try:
            genes.append(int(g))
        except ValueError:
        
            # switch to MySQL wildcard matching
            g = g.replace('*', '%').replace('?', '_')
        
            if species:
                newgenes = [r.entrez_id for r in Gene.objects.filter(symbol__iexact=g, tax_id=species)]
                newgenes = [r.entrez_id for r in Gene.objects.filter(tax_id=species).extra(where=['`symbol` LIKE %s'], params=[g])]
            else:
                newgenes = [r.entrez_id for r in Gene.objects.extra(where=['`symbol` LIKE %s'], params=[g])]
            
            if newgenes:
                genes.extend(newgenes)
            else:
                raise KeyError(g) # we couldn't find a match for one of the genes
                
    return genes


def parseboolean(s):
    """Get a boolean argument from the query string, and decide if it's true or false"""
    
    if type(s) is bool:
        return s
    
    if s.isdigit():
        return int(s)
    
    if s.lower() in ('', 'off','f','false','no','none','undefined'):
        return False
    else:
        return True


def genesearch(request):
    """Does the actual search for the gene search.  Given a keyword query,
    a list of genes, species, homology option, offset, limit, sorting
    criterion, and response type (all via the query string), fetches a list of
    genes relevent to the query via the index and database, and returns the 
    appropriate response."""
    
    # format to return the results in (blank for JSON to display in the browser)
    download = request.GET.get('download')
    
    # get species, default=human
    try:
        species = int(request.GET['species'])
    except (KeyError, ValueError):
        species = 9606
        
    # get homology option
    try:
        usehomologs = parseboolean(request.GET['usehomologs'])
    except (KeyError, ValueError):
        usehomologs = False
        
    # use homology option to decide which gene-abstract table and which
    # abstract-count column to use.
    if usehomologs:
        geneabstract_tablename = 'homologene_gene_abstract'
        abstract_col = 'homolog_abstracts'
    else:
        geneabstract_tablename = 'gene_abstract'
        abstract_col = 'abstracts'
    
    # get genes
    geneinput = request.GET.get('genes')
    if geneinput:
        try:
            genes = gene_lookup(geneinput, species)
        except KeyError as (e,):
            return searchresponse(validresult=False, download=download, errmsg='No genes match "{0}" for species {1}'.format(e, species))
    else:
        genes = None
    
    # get keywords
    keywords = request.GET.get('q')
    
    # don't do anything if we don't have a query
    if not genes and not keywords:
        return searchresponse(validresult=False, download=download, errmsg="Please enter gene symbols or a keyword query.")
    
    # get abstracts matching keywords and genes
    abstracts = get_abstracts(keywords, genes, usehomologs)
    query_abstract_count = len(abstracts)

    # error if no abstracts matched the query
    if abstracts == []:
        return searchresponse(validresult=False, download=download, errmsg="Your query did not match any abstracts.", query=keywords, genes=genes, usehomologs=usehomologs)

    # get corpus size
    total_abstract_count = corpus_size()

    # get limit and offset from query string
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    
    try: 
        limit = int(request.GET.get('limit')) # limit to display to user
        query_limit = limit # limit to insert into SQL
    except: 
        limit = None
        query_limit = 18446744073709551615 # arbitrary large number (no better way to do this.)
    
    # dict of valid orderby options, and corresponding terms for SQL query
    _query_orderbys = {'adjusted_precision': 'precision',
        'matching_abstracts': 'hits', 'total_abstracts': 'abstracts_display',
        'f1_score': 'f1_score'}
    
    # get the order from the query string
    orderby = request.GET.get('orderby', default='f1_score')
    # make sure that the order-by option is valid, to prevent SQL injection
    if orderby not in _query_orderbys:
        orderby = 'f1_score'
    query_orderby = _query_orderbys[orderby] # orderby term to insert into SQL

    def paramstring(l):
        """Return a string of comma-separated %s's of length l
        (faster and more memory-efficient than using a list comprehension)"""
        def slist():
            for i in xrange(l): yield "%s"
        return ','.join(slist())
    
    # build SQL query for fetching genes
    sqlquery = """
    SELECT g.*, 
        `{abstract_col}` `abstracts_display`,
        COUNT(*) hits, 
        COUNT(*)/ (`{abstract_col}` + 10) `precision`,
        (2 * (COUNT(*) / `{abstract_col}`) * (COUNT(*) / {query_abstract_count})) / 
            ((COUNT(*) / `{abstract_col}`) + (COUNT(*) / {query_abstract_count})) f1_score
    FROM `{geneabstract_tablename}` a
    INNER JOIN `gene` g
    ON g.entrez_id = a.gene
    WHERE a.`abstract` in ({paramstring})
    AND g.`tax_id` = %s
    GROUP BY g.entrez_id
    ORDER BY `{orderby}` DESC
    LIMIT %s, %s;
    """.format(
        paramstring=paramstring(len(abstracts)), 
        orderby=query_orderby, 
        query_abstract_count=query_abstract_count,
        species=species,
        geneabstract_tablename=geneabstract_tablename,
        abstract_col=abstract_col)
    
    # execute sql query, get genes
    results = Gene.objects.raw(sqlquery, abstracts + [species, offset, query_limit])
    
    # calculate p values
    phyper = robjects.r['phyper']
    pvals = ['{0:.2e}'.format(phyper(g.hits-1, query_abstract_count, total_abstract_count-query_abstract_count, g.abstracts_display, lower_tail=False)[0]) for g in results]

    if not pvals: 
        return searchresponse(validresult=False, download=download, errmsg="Your query didn't match any genes.", query=keywords, genes=genes, usehomologs=usehomologs, species=species)

    return searchresponse(validresult=True, download=download, results=results, genes=genes, pvals=pvals, offset=offset, orderby=orderby, query=keywords, limit=limit, usehomologs=usehomologs, species=species)
    

def searchresponse(validresult, download=None, errmsg=None, results=[], genes=[], pvals=[], offset=0, orderby=None, query=None, limit=None, usehomologs=None, species=None):
    """Return an HttpResponse object with gene search results, as either JSON, XML,
    or a CSV depending on the "download" argument.  "validresult" is True if "genes",
    "pvals", and "offset" represent a valid result, and False otherwise.  "errmsg" 
    is an error message to display to the user."""

    if download:
        if not query and not genes: 
            raise Http404 # 404 if we don't have a query
    
        if download.lower() == 'csv':
            # create, package, and return a CSV file
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = \
                'attachment; filename=gadget-{0}-{1}.csv'.format(quote(query), ','.join([str(g) for g in genes]) if genes else '')
            response.write(makeCSV(results, pvals, offset))
            return response
            
        elif download.lower() == 'xml':
            # render the XML template
            # look up gene symbols in database
            generecs = Gene.objects.filter(entrez_id__in=genes).only('entrez_id', 'symbol') if genes else []
            response = render_to_response('genelist.xml', 
                {'results': zip(results, pvals), 'pvals': pvals, 'offset': offset, 
                'orderby':orderby, 'q':query, 'limit':limit, 'errmsg': errmsg,
                'genes': generecs, 'usehomologs': usehomologs, 'species':species})
            response['Content-Type'] = 'text/xml'
            return response
            
        else:
            raise Http404 # 404 if invalid "download" argument
        
    else: # display results in web browser
        # render results to html
        if validresult:
            resulthtml = render_to_string('genelist.html', {'results': zip(results, pvals), 'pvals': pvals, 'offset': offset})
        else:
            resulthtml = None

        # render and return JSON
        response = HttpResponse()
        json.dump({'validresult': validresult, 'errmsg': errmsg, 'result': resulthtml}, response)
        return response


def makeCSV(genes, pvals, offset):
    """Create a CSV file (returned as a string) given a list of genes and a list of p values."""
    header = 'rank,f1_score,matching_abstracts,total_abstracts,adjusted_precision,p_value,symbol,name,synonyms,entrez_id,chromosome,map_location\n'
    body = '\n'.join([','.join(['"{0}"'.format(f) for f in 
        (rank, '{0:0.3f}'.format(g.f1_score), g.hits, g.abstracts_display, '{0:0.3f}'.format(g.precision), p, g.symbol, g.name, g.synonyms, g.entrez_id, g.chromosome, g.maplocation)])
        for rank, (g, p) in enumerate(zip(genes, pvals), start=1+offset)])
    return header + body


def abstracts(request):
    """Return a list of abstracts (as HTML wrapped in JSON) for a keyword
    query and list of genes."""

    # get species, default=human
    try:
        species = int(request.GET['species'])
    except (KeyError, ValueError):
        species = 9606
    
    # get query arguments from query string
    keywords = request.GET.get('q')
    try:
        genes = gene_lookup(request.GET.get('genes'), species)
    except KeyError:
        # bad gene query
        raise Http404
    
    # figure out if we should include homologs
    try:
        usehomologs = parseboolean(request.GET['usehomologs'])
    except (KeyError, ValueError):
        usehomologs = False
    
    # error if no query
    if not keywords and not genes:
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'You must supply either genes or a query'}, response)
        return response
    
    # get abstract ID's from index
    abstract_ids = get_abstracts(keywords, genes, usehomologs)
    
    # error if no abstracts
    if not abstract_ids:
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'No more abstracts!'}, response)
        return response
    
    # apply limit and offset
    # get optional limit and offset parameters
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    try: limit = int(request.GET.get('limit'))
    except: limit = 18446744073709551615 # arbitrary large number
    abstract_ids = abstract_ids[offset:limit+offset]
    
    # fetch rows from database
    abstracts = Abstract.objects.filter(pubmed_id__in=abstract_ids)
    
    # create response
    resulthtml = render_to_string('abstracts.html', {'abstracts': abstracts})
    response = HttpResponse()
    json.dump({'validresult': True, 'result': resulthtml}, response)
    return response

