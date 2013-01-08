#!/usr/bin/python
import json

from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.http import HttpResponse
from django import forms

from genetext.keyphraseview.models import KeyPhrase
from genetext.abstracts.index import get_abstracts
from genetext.geneview.geneview import searchparams, speciesnames, \
    specieschoices, geneoperators, parseboolean, validatespecies
from genetext.geneindex.geneindex import parse_abstractquery, flatten_query

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
    
    return render_to_response('keyphrasesearch.html', {'form': form, 'q': q, 
        'genes': genes, 'geneop': geneop, 'genesyms': genesyms, 'species': species, 
        'speciesname': speciesname, 'usehomologs': usehomologs, 'orderby': orderby})


def keyphrasesearch(request):
    # parse search parameters out of the query string
    params = searchparams(request)
    
    if params.genes:
        try:
            # get a gene query to run against the abstract index
            genequery = parse_abstractquery(params.genes, params.species, params.implicitOr, params.usehomologs)
        except LookupError as e:
            # a term in the gene query couldn't be matched to any genes.
            return searchresponse(False, params, errmsg='No genes match <b>{0}</b> for species {1}'.format(e.args[0], params.species))
    else:
        genequery = None
    
    # use homology option to decide which gene-abstract table to use
    if params.usehomologs:
        geneabstract_tablename = 'homologene_gene_abstract'
    else:
        geneabstract_tablename = 'gene_abstract'
    
    # from the gene query, get a list of the gene ID's in the query (as strings)    
    genelist = map(str, flatten_query(genequery))
    
    # get abstracts matching keywords and genes
    abstracts = get_abstracts(params.keywords, genequery, params.usehomologs)
    
    def paramstring(l):
        """Return a string of comma-separated %s's of length l
        (faster and more memory-efficient than using a list comprehension)"""
        def slist():
            for i in xrange(l): yield "%s"
        return ','.join(slist())
    
    sqlquery = \
    """
    select
    k.`id`,
    k.`string` string,
    count(distinct g_all.`entrez_id`) all_genes,
    count(distinct ga_query.`gene`) query_genes,
    
    count(distinct ga_query.`gene`) / {gene_list_size} gene_recall,
    count(distinct ga_query.`gene`) / count(distinct g_all.`entrez_id`) gene_precision,

    2 * (count(distinct ga_query.`gene`) / count(distinct g_all.`entrez_id`))
    * (count(distinct ga_query.`gene`) / {gene_list_size}) /
    ((count(distinct ga_query.`gene`) / count(distinct g_all.`entrez_id`))
    + (count(distinct ga_query.`gene`) / {gene_list_size})) gene_f1_score
  
    from `keyphrase` k
    inner join `keyphrase_abstract` ka
    on ka.`keyphrase` = k.`id`

    left join `{geneabstract_tablename}` ga_all
    on ka.`abstract` = ga_all.`abstract`
    inner join `gene` g_all
    on g_all.`entrez_id` = ga_all.`gene`

    left join `{geneabstract_tablename}` ga_query
    on ka.abstract = ga_query.abstract

    where ka.abstract in ({abstract_param_list})
    and ga_query.`gene` in ({genes_param_list})
    and g_all.`tax_id` = %s

    group by k.`id`
    order by gene_f1_score desc
    limit %s, %s
    """.format(geneabstract_tablename=geneabstract_tablename,
    abstract_param_list=paramstring(len(abstracts)),
    genes_param_list=paramstring(len(genelist)),
    gene_list_size=len(genelist))
    
    result = KeyPhrase.objects.raw(sqlquery, abstracts + genelist + [params.species, params.offset, params.query_limit])
    
    # Check to see if the resultset is empty.  Django's RawQuerySet object 
    # doesn't have an empty() or __len__(), and is always True.
    # So, try getting the first item instead.
    try:
        result[0]
    except IndexError:
        return searchresponse(False, params, errmsg="Your query didn't match any keywords!")

    return searchresponse(True, params, result=result)


def searchresponse(validresult, params, result=[], errmsg=None):
    if validresult:
        # render results to html
        resulthtml = render_to_string('keyphraselist.html', {'result':result, 'params':params})
    else:
        resulthtml = None
       
    # render and return JSON    
    response = HttpResponse()
    json.dump({'validresult': validresult, 'errmsg': errmsg, 'result': resulthtml}, response)
    return response
        
        
        
