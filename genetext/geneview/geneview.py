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
from genetext.geneindex.geneindex import parse_abstractquery 

# allowable species (specieschoices should be in order, with the default first)
speciesnames = {'9606': 'Homo sapiens', '10090': 'Mus musculus', '559292': 'Saccharomyces cerevisiae'}
specieschoices = (('9606', 'Homo sapiens'),('10090', 'Mus musculus'), ('559292', 'Saccharomyces cerevisiae'))

geneoperators = (('any', 'any'), ('all','all'))
    
# dict of valid orderby options, and corresponding terms for SQL query
query_orderbys = {'adjusted_precision': 'precision',
    'matching_abstracts': 'hits', 'total_abstracts': 'abstracts_display',
    'f1_score': 'f1_score'}


def validatespecies(taxid):
    """Return a validated species ID and speciesname.  Human by default"""
    if taxid in speciesnames:
        return taxid, speciesnames[taxid]
    else:
        return '9606', speciesnames['9606']


def searchpage(request):
    """The search page for the word view (makes the forms)"""
    
    class SearchForm(forms.Form):
        q = forms.CharField(label='Keywords')
        genes = forms.CharField(label='Gene symbols')
        geneop = forms.ChoiceField(label='Gene operator', choices=geneoperators, widget=forms.RadioSelect, initial='any')
        species = forms.ChoiceField(label='Species', choices=specieschoices, initial='9606')
        usehomologs = forms.BooleanField(label='Use homologs', widget=forms.CheckboxInput(check_test=parseboolean))
    
    form = SearchForm(request.GET)
    
    # get form arguments from the query string
    q = request.GET.get('q', default='')
    genes = request.GET.get('genes', default='')
    geneop = request.GET.get('geneop', default=geneoperators[0][0])
    species = request.GET.get('species', default='9606')
    usehomologs_input = request.GET.get('usehomologs', default='')
    orderby = request.GET.get('orderby', default='f1_score')
    
    # validate species
    species, speciesname = validatespecies(request.GET.get('species'))

    # gene input to display to the user
    genesyms = genes
    
    usehomologs = parseboolean(usehomologs_input)
    
    return render_to_response('genesearch.html', {'form': form, 'q': q, 
        'genes': genes, 'geneop': geneop, 'genesyms': genesyms, 'species': species, 
        'speciesname': speciesname, 'usehomologs': usehomologs, 'orderby': orderby})


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


class searchparams:
    """Struct for arguments passed to the gene search via the query string.
    Parses the arguments out of the request object when initialized.
    Also used by the keyphrase search."""

    def __init__(self, request):
        # format to return the results in (blank for JSON to display in the browser)
        self.download = request.GET.get('download')

        # get species, default=human
        try:
            self.species = int(request.GET['species'])
        except (KeyError, ValueError):
            self.species = 9606
            
        # get homology option
        try:
            self.usehomologs = parseboolean(request.GET['usehomologs'])
        except (KeyError, ValueError):
            self.usehomologs = False
        
        # get keywords
        self.keywords = request.GET.get('q')

        # get gene operator (any (or) / all (and))
        try:
            self.geneop = request.GET['geneop'].lower()
            if self.geneop == 'all':
                self.implicitOr = False
            else:
                self.geneop = 'any'
                self.implicitOr = True
        except KeyError:
            self.geneop = 'any'
            self.implicitOr = True
    
        # get genes
        self.genes = request.GET.get('genes')

        # get offset (how many genes to skip, from the start of the list)
        try: self.offset = int(request.GET.get('offset'))
        except: self.offset = 0
        
        # get limit (max number of genes to return)
        try: 
            self.limit = int(request.GET.get('limit')) # limit to display to user
            self.query_limit = self.limit # limit to insert into SQL
        except: 
            self.limit = None
            self.query_limit = 9999999999999999999 # arbitrary large number
        
        # get the order from the query string
        self.orderby = request.GET.get('orderby', default='f1_score').lower()


def genesearch(request):
    """Does the actual search for the gene search.  Given a keyword query,
    a list of genes, species, homology option, offset, limit, sorting
    criterion, and response type (all via the query string), fetches a list of
    genes relevent to the query via the index and database, and returns the 
    appropriate response."""
    
    params = searchparams(request)
        
    # use homology option to decide which gene-abstract table and which
    # abstract-count column to use.
    if params.usehomologs:
        geneabstract_tablename = 'homologene_gene_abstract'
        abstract_col = 'homolog_abstracts'
    else:
        geneabstract_tablename = 'gene_abstract'
        abstract_col = 'abstracts'
    
    if params.genes:
        try:
            # get a query to run against the abstract index
            genequery = parse_abstractquery(params.genes, params.species, params.implicitOr, params.usehomologs)
        except LookupError as e:
            # a term in the gene query couldn't be matched to any genes.
            return searchresponse(validresult=False, download=params.download, errmsg='No genes match <b>{0}</b> for species {1}'.format(e.args[0], params.species))
    else:
        genequery = None
    
    # don't do anything if we don't have a query
    if not genequery and not params.keywords:
        return searchresponse(validresult=False, download=params.download, errmsg="Please enter gene symbols or a keyword query.")
    
    # get abstracts matching keywords and genes
    abstracts = get_abstracts(params.keywords, genequery, params.usehomologs)
    query_abstract_count = len(abstracts)

    # error if no abstracts matched the query
    if abstracts == []:
        return searchresponse(validresult=False, download=params.download, errmsg="Your query did not match any abstracts.", query=params.keywords, genes=params.genes, usehomologs=params.usehomologs)

    # get corpus size
    total_abstract_count = corpus_size()

    if params.orderby in query_orderbys:
        query_orderby = query_orderbys[params.orderby] # orderby term to insert into SQL
    else:
        query_orderby = params.orderby = 'f1_score'

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
        species=params.species,
        geneabstract_tablename=geneabstract_tablename,
        abstract_col=abstract_col)
    
    # execute sql query, get genes
    results = Gene.objects.raw(sqlquery, abstracts + [params.species, params.offset, params.query_limit])
    
    # calculate p values
    phyper = robjects.r['phyper']
    pvals = ['{0:.2e}'.format(phyper(g.hits-1, query_abstract_count, total_abstract_count-query_abstract_count, g.abstracts_display, lower_tail=False)[0]) for g in results]

    if not pvals: 
        return searchresponse(validresult=False, download=params.download, errmsg="Your query didn't match any genes.", query=params.keywords, genes=params.genes, usehomologs=params.usehomologs, species=params.species)

    return searchresponse(validresult=True, download=params.download, results=results, genes=params.genes, geneop=params.geneop, pvals=pvals, offset=params.offset, orderby=params.orderby, query=params.keywords, limit=params.limit, usehomologs=params.usehomologs, species=params.species, query_abstract_count=query_abstract_count)
    

def searchresponse(validresult, download=None, errmsg=None, results=[], genes=[], geneop=None, pvals=[], offset=0, orderby=None, query=None, limit=None, usehomologs=None, species=None, query_abstract_count=None):
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
                'attachment; filename=gadget-{0}-{1}.csv'.format(quote(query) if query else '', quote(genes) if genes else '')
            response.write(makeCSV(results, pvals, offset))
            return response
            
        elif download.lower() == 'xml':
            # render the XML template
            response = render_to_response('genelist.xml', 
                {'results': zip(results, pvals), 'pvals': pvals, 'offset': offset, 
                'orderby':orderby, 'q':query, 'limit':limit, 'errmsg': errmsg,
                'genes': genes, 'geneop': geneop, 'usehomologs': usehomologs, 'species':species})
            response['Content-Type'] = 'text/xml'
            return response
            
        else:
            raise Http404 # 404 if invalid "download" argument
        
    else: # display results in web browser
        # render results to html
        if validresult:
            resulthtml = render_to_string('genelist.html', {'results': zip(results, pvals), 'pvals': pvals, 'offset': offset, 'orderby': orderby})
        else:
            resulthtml = None

        # render and return JSON
        response = HttpResponse()
        json.dump({'validresult': validresult, 'errmsg': errmsg, 'result': resulthtml, 'abstractcount': query_abstract_count}, response)
        return response


def makeCSV(genes, pvals, offset):
    """Create a CSV file (returned as a string) given a list of genes and a list of p values."""
    header = 'rank,f1_score,matching_abstracts,total_abstracts,adjusted_precision,p_value,symbol,name,synonyms,entrez_id,chromosome,map_location\n'
    body = '\n'.join([','.join(['"{0}"'.format(f) for f in 
        (rank, '{0:0.3f}'.format(g.f1_score), g.hits, g.abstracts_display, '{0:0.3f}'.format(g.precision), p, g.symbol, g.name, g.synonyms, g.entrez_id, g.chromosome, g.maplocation)])
        for rank, (g, p) in enumerate(zip(genes, pvals), start=1+offset)])
    return header + body

