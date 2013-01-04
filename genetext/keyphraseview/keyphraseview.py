from genetext.keyphraseview.models import KeyPhrase

from genetext.abstracts.index import get_abstracts
from genetext.geneview.geneview import searchparams
from genetext.geneindex.geneindex import parse_abstractquery, flatten_query

from django.shortcuts import render_to_response

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
    
    count(distinct ga_query.`gene`) / {gene_list_size} recall,
    count(distinct ga_query.`gene`) / count(distinct g_all.`entrez_id`) kprecision,

    2 * (count(distinct ga_query.`gene`) / count(distinct g_all.`entrez_id`))
    * (count(distinct ga_query.`gene`) / {gene_list_size}) /
    ((count(distinct ga_query.`gene`) / count(distinct g_all.`entrez_id`))
    + (count(distinct ga_query.`gene`) / {gene_list_size})) f1_score
  
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
    """.format(geneabstract_tablename=geneabstract_tablename,
    abstract_param_list=paramstring(len(abstracts)),
    genes_param_list=paramstring(len(genelist)),
    gene_list_size=len(genelist))
    
    result = KeyPhrase.objects.raw(sqlquery, abstracts + genelist + [params.species])
    
    return render_to_response('keyphraselist.html', {'result':result})

def searchresponse(validresult, params, errmsg=None):
    return None
