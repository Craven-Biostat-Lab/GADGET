import json
from django.http import HttpResponse
from django.template.loader import render_to_string
from models import GeneCrossref

from django.shortcuts import render_to_response

class xreftype:
    def __init__(self, description=None, urlformat=None, category=None):
        self.description = description
        self.urlformat = urlformat
        self.category = category
nullxreftype = xreftype()

# hard code database names, urls, and categories
xreftypes = {
    'BioGPS': xreftype('BioGPS', 'http://biogps.org/#goto=genereport&id={id}', 'Expression'),
    'CleanEx': xreftype('CleanEx', 'http://cleanex.vital-it.ch/cgi-bin/get_doc?db=cleanex&format=nice&entry={id}', 'Expression'),
    'DMDM': xreftype('Domain Mapping of Disease Mutations (DMDM)', 'http://bioinf.umbc.edu/dmdm/gene_prot_page.php?search_type=protein&id={id}', 'Disease'),
    'DisProt': xreftype('Database of Protein Disorder (DisProt)', 'http://www.disprot.org/protein.php?id={id}', 'Disease'),
    'DrugBank': xreftype('DrugBank', 'http://www.drugbank.ca/drugs/{id}', 'Drugs'),
    'EMBL': xreftype('EMBL Nucleotide Sequence', 'http://www.ebi.ac.uk/ena/data/view/{id}', 'Sequence'),
    'EMBL-CDS': xreftype('EMBL Coding Sequence', 'http://www.ebi.ac.uk/ena/data/view/{id}', 'Sequence'),
    'Ensembl': xreftype('Ensembl ID', 'http://ensembl.org/Gene/Variation_Gene/Table?g={id}', 'General'),
    'Ensembl_PRO': xreftype('Ensembl Protein', None, 'Protein'),
    'Ensembl_TRS': xreftype('Ensemble Transcript', None, 'Sequence'),
    'GI': xreftype('Genbank GenInfo ID', 'http://www.ncbi.nlm.nih.gov/nucleotide/{id}', 'General'),
    'GeneCards': xreftype('GeneCards', 'http://www.genecards.org/cgi-bin/carddisp.pl?gene={id}', 'General'),
    'GeneID': xreftype('Entrez Gene ID', 'http://www.ncbi.nlm.nih.gov/gene?term={id}', 'General'),
    'GermOnline': xreftype('GermOnline', 'http://www.germonline.org/Homo_sapiens/geneview?gene={id}', 'General'),
    'H-InvDB': xreftype('H-Invitational Database', 'http://h-invitational.jp/hinv/spsoup/locus_view?hix_id={id}', 'General'),
    'HGNC': xreftype('HUGO Gene Nomenclature Committee', 'http://www.genenames.org/data/hgnc_data.php?hgnc_id={id}', 'General'),
    'HOVERGEN': xreftype('HOVERGEN gene family', 'http://pbil.univ-lyon1.fr/cgi-bin/acnuc-dispfam?db=HOVERGEN&query={id}', 'Homology'),
    'HPA': xreftype('Human Protein Atlas', 'http://www.proteinatlas.org/search/{id}', 'Protein'),
    'IPI': xreftype('International Protein Index (IPI)', None, 'Protein'),
    'KEGG': xreftype('Kyoto Encyclopedia of Genes and Genomes (KEGG)', 'http://www.genome.jp/dbget-bin/www_bget?{id}', 'Interactions'),
    'KO': xreftype('Kegg Orthology', 'http://www.genome.jp/dbget-bin/www_bget?ko:{id}', 'Homology'),
    'MGI': xreftype('Mouse Genome Informatics (MGI)', 'http://www.informatics.jax.org/marker/{id}', 'General'),
    'MIM': xreftype('Mendelian Inheritance in Man (MIM)', 'http://omim.org/entry/{id}', 'Disease'),
    'MINT': xreftype('MINT', 'http://mint.bio.uniroma2.it/mint/search/search.do?queryType=protein&interactorAc={id}', None),
    'NCBI_TaxID': xreftype('NCBI Taxon ID', 'http://www.ncbi.nlm.nih.gov/taxonomy?term={id}', None),
    'NextBio': xreftype('NextBio', None, 'Expression'),
    'OrthoDB': xreftype('OrthoDB', None, 'Homology'),
    'Orphanet': xreftype('Orphanet', 'http://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=EN&Expert={id}', 'Disease'),
    'PDB': xreftype('Protein Data Bank (PDB)', 'http://www.rcsb.org/pdb/explore/explore.do?structureId={id}', 'Protein'),
    'PharmGKB': xreftype('PharmGKB', 'http://www.pharmgkb.org/gene/{id}', 'Drugs'),
    'Reactome': xreftype('Reactome', 'http://www.reactome.org/cgi-bin/search2?OPERATOR=ALL&QUERY={id}', 'Interactions'),
    'RefSeq': xreftype('RefSeq', 'http://www.ncbi.nlm.nih.gov/entrez/viewer.cgi?val={id}', 'Sequence'),
    'RefSeq_NT': xreftype('RefSeq NT', 'http://www.ncbi.nlm.nih.gov/entrez/viewer.cgi?val={id}', 'Sequence'),
    'SGD': xreftype('Saccharomyces Genome Database (SGD)', 'http://www.yeastgenome.org/cgi-bin/locus.fpl?dbid={id}', 'General'),
    'TCDB': xreftype('Transporter Classification Database (TCDB)', 'http://www.tcdb.org/search/result.php?tc={id}', None),
    'UCSC': xreftype('UCSC Description Page', 'http://genome.ucsc.edu/cgi-bin/hgGene?hgg_gene={id}', 'General'),
    'UniGene': xreftype('UniGene', 'http://www.ncbi.nlm.nih.gov/unigene?term={id}', 'General'),
    'UniParc': xreftype('UniParc', 'http://www.uniprot.org/uniparc/{id}', 'Protein'),
    'UniProtKB-AC': xreftype('UniProtKB Accession', 'http://www.uniprot.org/uniprot/{id}', 'Protein'),
    'UniProtKB-ID': xreftype('UniProtKB ID', 'http://www.uniprot.org/uniprot/{id}', 'Protein'),
    'UniRef100': xreftype('UniRef 100', 'http://www.uniprot.org/uniref/{id}', 'Homology'),
    'UniRef50': xreftype('UniRef 50', 'http://www.uniprot.org/uniref/{id}', 'Homology'),
    'UniRef90': xreftype('UniRef 90', 'http://www.uniprot.org/uniref/{id}', 'Homology'),
    'eggNOG': xreftype('eggNOG', 'http://eggnog.embl.de/version_3.0/cgi/search.py?search_term_0={id}', 'Homology'),
    'neXtProt': xreftype('neXtProt', 'http://www.nextprot.org/db/entry/{id}', 'Protein'),
    }

categoryorder = {
    'General': 1,
    'Sequence': 2,
    'Expression': 3,
    'Homology': 4,
    'Protein': 5,
    'Interactions': 6,
    'Disease': 7,
    'Drugs': 8,
    None: 9,
    }


def xreflookup(gene_entrez_id):
    """Look up cross references for a given gene ID from the database"""
    return GeneCrossref.objects.filter(entrez_id=gene_entrez_id).order_by('idtype')


def formatlinks(xrefs):
    """Add a "url" attribute to each item in a list of crossrefs, by formatting
    the appropriate string in the urlformats dict with the crossref ID."""
    
    for xref in xrefs:
        if xref.idtype in xreftypes and xreftypes[xref.idtype].urlformat:
            xref.url = xreftypes[xref.idtype].urlformat.format(id=xref.crossref_id)


def groupxrefs(xrefs):
    """Take a list of xrefs (Django database rows) as input, and organize and 
    return them as categories.  Return a sorted list of categories, each with 
    a name, and a list of databases ('name' and 'dblist').  
    
    Each database (class: xrefdb' has an 'idtype' from the, an 'xreftype' 
    associated with a description and url format (see above), and an 'idlist',
    containing the original xref objects."""
    # struct for holding information about a crossref database.
    # A database can have multiple associated ID's for a gene.
    class xrefdb:
        def __init__(self, idtype, xreftype):
            self.idtype = idtype
            self.xreftype = xreftype
            self.xreflist = []
    
    # all the databases in the list of crossrefs, keys are ID types, values are 'xrefdb's.   
    xrefdbs = dict()
    
    # iterate over xrefs, associate each one with a database.
    # xrefs should already be sorted by 'idtype'
    for xref in xrefs:
        if xref.idtype not in xrefdbs:
            xrefdbs[xref.idtype] = xrefdb(xref.idtype, xreftypes.get(xref.idtype, nullxreftype))
        xrefdbs[xref.idtype].xreflist.append(xref)
    
    # categories of crossrefs
    class xrefcat:
        def __init__(self, name):
            self.name = name
            self.dblist = []        
    xrefcats = dict()        
    
    # put crossref databases into categories        
    for xdb in xrefdbs.values():
        if xdb.xreftype.category not in xrefcats:
            xrefcats[xdb.xreftype.category] = xrefcat(xdb.xreftype.category)
        xrefcats[xdb.xreftype.category].dblist.append(xdb) 

    # sort database lists
    for cat in xrefcats.values():
        cat.dblist.sort(key=lambda db: db.idtype.upper())
        
    # sort and return categories
    return list(sorted(xrefcats.values(), key=lambda x: categoryorder[x.name]))


def genecrossrefs(request):
    """Return a page of links to external databases for a given gene"""

    # get gene ID out of query string
    try:
        gene_entrez_id = int(request.GET['gene'])
    except (KeyError, ValueError):
        # error if we don't have a gene ID
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'You need a gene ID to look up crossrefs'}, response)
        return response
    
    # get gene symbol from query string
    genesymbol = request.GET.get('genesymbol')

    # get cross references from database
    xrefs = xreflookup(gene_entrez_id)
    
    # format link URLS
    formatlinks(xrefs)
    
    # put xrefs into groups of ID types
    xrefcats = groupxrefs(xrefs)
            
    # render and return response
    resulthtml = render_to_string('genecrossrefs.html', {'genesymbol': genesymbol,
        'xrefcats': xrefcats})
    response = HttpResponse()
    json.dump({'validresult': True, 'result': resulthtml}, response)
    return response 
