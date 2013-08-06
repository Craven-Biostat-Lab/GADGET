#!/usr/bin/python
import json
from urllib import quote

from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.http import HttpResponse
from django import forms

from genetext.keyphraseview.models import KeyPhrase
from genetext.abstracts.index import get_abstracts
from genetext.geneview.geneview import searchparams, speciesnames, \
    specieschoices, geneoperators, parseboolean, validatespecies
from genetext.geneindex.geneindex import parse_gene_abstractquery, genefile_lookup, BadGenefileError, flatten_query

# set of valid orderby options when genes are not provided
abstract_query_orderbys = set(['total_abstracts', 'query_abstracts',
    'abstract_precision', 'abstract_recall', 'abstract_f1_score'])

# set of valid orderby options when genes -are- provided
gene_query_orderbys = set(('total_genes', 'query_genes', 'gene_precision', 
    'gene_recall', 'gene_f1_score'))
gene_query_orderbys.update(abstract_query_orderbys)


def searchpage(request):
    """The search page for the word view (makes the forms)"""
    
    class SearchForm(forms.Form):
        q = forms.CharField(label='Keywords')
        genes = forms.CharField(label='Gene symbols')
        geneop = forms.ChoiceField(label='Gene operator', choices=geneoperators, widget=forms.RadioSelect, initial='any')
        usegenefile = forms.BooleanField(initial=False, widget=forms.HiddenInput())
        species = forms.ChoiceField(label='Species', choices=specieschoices, initial='9606')
        usehomologs = forms.BooleanField(label='Use homologs', widget=forms.CheckboxInput(check_test=parseboolean))
    
    form = SearchForm(request.GET)
    
    # get form arguments from the query string
    q = request.GET.get('q', default='')
    genes = request.GET.get('genes', default='')
    geneop = request.GET.get('geneop', default=geneoperators[0][0])
    usegenefile_input = request.GET.get('usegenefile', default=False)
    genefilename = request.COOKIES.get('genefilename')
    genefileID = request.COOKIES.get('genefileID')
    species = request.GET.get('species', default='9606')
    usehomologs_input = request.GET.get('usehomologs', default='')
    
    usegenefile = parseboolean(usegenefile_input)
    usehomologs = parseboolean(usehomologs_input)

    if genes or usegenefile:
        orderby = request.GET.get('orderby', default='gene_f1_score')
    else:
        orderby = request.GET.get('orderby', default='abstract_f1_score')
    
    # validate species
    species, speciesname = validatespecies(request.GET.get('species'))

    # gene input to display to the user
    genesyms = genes
        
    return render_to_response('keyphrasesearch.html', {'form': form, 'q': q, 
        'genes': genes, 'geneop': geneop, 'genesyms': genesyms, 'species': species, 
        'speciesname': speciesname, 'usehomologs': usehomologs, 'orderby': orderby,
        'usegenefile': usegenefile, 'genefilename': genefilename,
        'genefileID': genefileID})


def keyphrasesearch(request):
    # parse search parameters out of the query string
    params = searchparams(request)
    
    if params.genes or params.usegenefile:
        try:
            # get a gene query to run against the abstract index
            
            if params.usegenefile:
                # get genes from an uploaded file
                genequery = genefile_lookup(params.genefileID, implicitOr=params.implicitOr, usehomologs=params.usehomologs)
           
                if params.usehomologs:
                    genelist = map(str, flatten_query(genefile_lookup(params.genefileID, implicitOr=params.implicitOr, usehomologs=False)))
                else:
                     genelist = map(str, flatten_query(genequery))

            else:
                # get genes from the query string
                genequery = parse_gene_abstractquery(params.genes, params.species, params.implicitOr, params.usehomologs)

                # from the gene query, get a list of the gene ID's in the query (as strings)           
                if params.usehomologs:
                    genelist = map(str, flatten_query(parse_gene_abstractquery(params.genes, params.species, params.implicitOr, usehomologs=False)))
                else:
                     genelist = map(str, flatten_query(genequery))

        except LookupError as e:
            # a term in the gene query couldn't be matched to any genes.
            return searchresponse(False, params, errmsg='No genes match <b>{0}</b> for species {1}'.format(e.args[0], params.species))
        except BadGenefileError:
            return searchresponse(validresult=False, download=params.download, errmsg="Can't find this gene file!  It probably expired.  Please upload it again.""")
    else:
        genequery = None
        genelist = []

    print "keyphrase gene query", genequery
    
    # don't do anything if we don't have a query
    if not genequery and not params.keywords:
        return searchresponse(False, params, errmsg="Please enter gene symbols or a keyword query.")
    
    # use homology option to decide which gene-abstract table to use
    if params.usehomologs:
        geneabstract_tablename = 'homologene_gene_abstract'
    else:
        geneabstract_tablename = 'gene_abstract'
    
    # get abstracts matching keywords and genes
    abstracts = get_abstracts(params.keywords, genequery, params.usehomologs)
    
    # error if no abstracts matched the query
    if abstracts == []:
        return searchresponse(False, params, errmsg="Your query did not match any abstracts.")
        
    def paramstring(l):
        """Return a string of comma-separated %s's of length l
        (faster and more memory-efficient than using a list comprehension)"""
        def slist():
            for i in xrange(l): yield "%s"
        return ','.join(slist())
    
    if genelist:
        # query if we have genes
        
        if params.orderby in gene_query_orderbys:
            query_orderby = params.orderby
        else:
            query_orderby = 'gene_f1_score'
        
        sqlquery = \
        """
        select a.*, k.`string` `string`
        from (
        
          select
          ka.`keyphrase` `id`,
          kgc.`genecount` total_genes,
          count(distinct ga_query.`gene`) query_genes,
          
          count(distinct ga_query.`gene`) / {gene_list_size} gene_recall,
          count(distinct ga_query.`gene`) / kgc.`genecount` gene_precision,

          2 * (count(distinct ga_query.`gene`) / kgc.`genecount`)
          * (count(distinct ga_query.`gene`) / {gene_list_size}) /
          ((count(distinct ga_query.`gene`) / kgc.`genecount`)
          + (count(distinct ga_query.`gene`) / {gene_list_size})) gene_f1_score,
        
          ka.`abstractcount` total_abstracts,
          count(distinct ka.`abstract`) query_abstracts,
          
          count(distinct ka.`abstract`) / ka.`abstractcount` abstract_precision,
          count(distinct ka.`abstract`) / {abstract_list_size} abstract_recall,
          
          2 * (count(distinct ka.`abstract`) / ka.`abstractcount`)
          * (count(distinct ka.`abstract`) / {abstract_list_size}) /
          ((count(distinct ka.`abstract`) / ka.`abstractcount`)
          + (count(distinct ka.`abstract`) / {abstract_list_size})) abstract_f1_score
          
          from `keyphrase_abstract` ka

          inner join `keyphrase_genecounts` kgc
          on kgc.`keyphrase` = ka.`keyphrase`

          inner join `{geneabstract_tablename}` ga_query
          on ka.abstract = ga_query.abstract

          where ka.abstract in ({abstract_param_list})
          and ga_query.`gene` in ({genes_param_list})
          
          and kgc.`tax` = %s

          group by ka.`keyphrase`
          order by {query_orderby} desc
          limit %s, %s
        
        ) a
        inner join `keyphrase` k
        on k.`id` = a.`id`;
        """.format(geneabstract_tablename=geneabstract_tablename,
        abstract_param_list=paramstring(len(abstracts)),
        genes_param_list=paramstring(len(genelist)),
        gene_list_size=len(genelist),
        abstract_list_size=len(abstracts),
        query_orderby=query_orderby)
        
        #with open('/home/genetext/query.sql', 'w') as f:
        #    f.write(sqlquery % tuple(abstracts + genelist + [params.species, params.offset, params.query_limit]))
        
        result = KeyPhrase.objects.raw(sqlquery, abstracts + genelist + [params.species, params.offset, params.query_limit])
        
    else:
        # query if we don't have genes
        
        if params.orderby in abstract_query_orderbys:
            query_orderby = params.orderby
        else:
            query_orderby = 'abstract_f1_score'
        
        sqlquery = \
        """
        select a.*, k.`string`       

        from 
        (
          select
          ka.`keyphrase` `id`,
        
          null total_genes,
          null query_genes,
          null gene_recall,
          null gene_precision,
          null gene_f1_score,
          
          ka.`abstractcount` total_abstracts,
          count(distinct ka.`abstract`) query_abstracts,
          
          count(distinct ka.`abstract`) / ka.`abstractcount` abstract_precision,
          count(distinct ka.`abstract`) / {abstract_list_size} abstract_recall,
          
          2 * (count(distinct ka.`abstract`) / ka.`abstractcount`)
          * (count(distinct ka.`abstract`) / {abstract_list_size}) /
          ((count(distinct ka.`abstract`) / ka.`abstractcount`)
          + (count(distinct ka.`abstract`) / {abstract_list_size})) abstract_f1_score
          
          from `keyphrase_abstract` ka
   
          where ka.`abstract` in ({abstract_param_list})
          group by ka.`keyphrase`
          order by {query_orderby} desc
          limit %s, %s
        ) a
        inner join `keyphrase` k
        on k.`id` = a.`id`
        """.format(abstract_param_list=paramstring(len(abstracts)),
        abstract_list_size=len(abstracts),
        query_orderby=query_orderby)
    
        #with open('/home/genetext/query.sql', 'w') as f:
        #    f.write(sqlquery % tuple(abstracts + [params.offset, params.query_limit]))
    
        result = KeyPhrase.objects.raw(sqlquery, abstracts + [params.offset, params.query_limit])
    
    # Check to see if the resultset is empty.  Django's RawQuerySet object 
    # doesn't have an empty() or __len__(), and is always True.
    # So, try getting the first item instead.
    try:
        result[0]
    except IndexError:
        return searchresponse(False, params, errmsg="Your query didn't match any keywords!")

    return searchresponse(True, params, result=result, abstractcount=len(abstracts))


def searchresponse(validresult, params, result=[], errmsg=None, abstractcount=None):
    if params.download:
        if params.download.lower() == 'csv':
        # create, package, and return a CSV file
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = \
                'attachment; filename=gadget-keywords-{0}-{1}.csv'.format(quote(params.keywords) if params.keywords else '', quote(params.genes) if params.genes else '')
            if validresult:
                response.write(makecsv(params, result))
            else:
                response.write('Error: ' + str(errmsg))
            return response

    else:
        # no download option, display results in web browser
        if validresult:
            # render results to html
            resulthtml = render_to_string('keyphraselist.html', {'result':result, 
                'params':params, 'abstractcount':abstractcount})
        else:
            resulthtml = None
           
        # render and return JSON    
        response = HttpResponse()
        json.dump({'validresult': validresult, 'errmsg': errmsg, 'result': resulthtml,
            'abstractcount':abstractcount}, response)
        return response
        
        
def makecsv(params, result):
    """Create a CSV file from keyphrase results"""
    header = 'rank,text,total_genes,query_genes,gene_precision,gene_recall,gene_f1,total_abstracts,query_abstracts,abstract_precision,abstract_recall,abstract_f1\n'
    try:
        body = '\n'.join([','.join(
            (
            str(rank), 
            k.string, 
            str(k.total_genes) if k.total_genes else '-', 
            str(k.query_genes) if k.query_genes else '-', 
            '{0:0.3f}'.format(k.gene_precision) if k.gene_precision else '-', 
            '{0:0.3f}'.format(k.gene_recall) if k.gene_recall else '-', 
            '{0:0.3f}'.format(k.gene_f1_score) if k.gene_f1_score else '-', 
            str(k.total_abstracts), 
            str(k.query_abstracts), 
            '{0:0.3f}'.format(k.abstract_precision), 
            '{0:0.3f}'.format(k.abstract_recall), 
            '{0:0.3f}'.format(k.abstract_f1_score)  )
            )
            for rank, k in enumerate(result, start=1+params.offset)])
    except:
        print rank, k.string, k.total_genes, k.query_genes, k.gene_precision, k.gene_recall, k.gene_f1_score, k.total_abstracts, k.query_abstracts, k.abstract_precision, k.abstract_recall, k.abstract_f1_score
        raise
        
    return header + body
        



        
