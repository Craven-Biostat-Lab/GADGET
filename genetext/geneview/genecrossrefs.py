import json
from django.http import HttpResponse
from django.template.loader import render_to_string
from genetext.geneview.models import GeneCrossref

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
    'MGI': xreftype('Mouse Genome Informatics (MGI)', 'http://www.informatics.jax.org/marker/{id}', 'Expression'),
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
    'SGD': xreftype('Saccharomyces Genome Database (SGD)', 'http://www.yeastgenome.org/cgi-bin/locus.fpl?dbid={id}', 'Expression'),
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

# hard code database names and urls
sourcenames = {
    'BioGPS': 'BioGPS',
    'CleanEx': 'CleanEx expression data',
    'DisProt': 'Database of Protein Disorder (DisProt)',
    'DMDM': 'Domain Mapping of Disease Mutations (DMDM)',
    'DrugBank': 'DrugBank',
    'EMBL': 'EMBL Nucleotide Sequence',
    'EMBL-CDS': 'EMBL Coding Sequence',
    'Ensembl': 'Ensembl ID',
    'Ensembl_PRO': 'Ensembl Protein',
    'Ensembl_TRS': 'Ensemble Transcript',
    'GI': 'Genbank GenInfo ID',
    'GeneCards': 'GeneCards',
    'GeneID': 'Entrez Gene ID',
    'GermOnline': 'GermOnline',
    'H-InvDB': 'H-Invitational Database',
    'HGNC': 'HUGO Gene Nomenclature Committee',
    'HOVERGEN': 'HOVERGEN gene family',
    'HPA': 'Human Protein Atlas',
    'IPI': 'International Protein Index (IPI)',
    'KEGG': 'Kyoto Encyclopedia of Genes and Genomes (KEGG)',
    'KO': 'Kegg Orthology',
    'MIM': 'Mendelian Inheritance in Man (MIM)',
    'MINT': 'MINT',
    'NCBI_TaxID': 'NCBI Taxon ID',
    'Orphanet': 'Orphanet',
    'PDB': 'Protein Data Bank (PDB)',
    'PharmGKB': 'PharmGKB',
    'Reactome': 'Reactome',
    'RefSeq': 'RefSeq',
    'RefSeq_NT': 'RefSeq NT',
    'TCDB': 'Transporter Classification Database (TCDB)',
    'UCSC': 'UCSC Description Page',
    'UniGene': 'UniGene',
    'UniParc': 'UniParc',
    'UniProtKB-AC': 'UniProtKB Accession',
    'UniProtKB-ID': 'UniProtKB ID',
    'UniRef100': 'UniRef 100',
    'UniRef90': 'UniRef 90',
    'UniRef50': 'UniRef 50',
    'eggNOG': 'eggNOG',
    'neXtProt': 'neXtProt',
    }
    
urlformats = {
    'BioGPS': 'http://biogps.org/#goto=genereport&id={id}',
    'CleanEx': 'http://cleanex.vital-it.ch/cgi-bin/get_doc?db=cleanex&format=nice&entry={id}',
    'DisProt': 'http://www.disprot.org/protein.php?id={id}',
    'DMDM': 'http://bioinf.umbc.edu/dmdm/gene_prot_page.php?search_type=protein&id={id}',
    'DrugBank': 'http://www.drugbank.ca/drugs/{id}',
    'EMBL': 'http://www.ebi.ac.uk/ena/data/view/{id}',
    'EMBL-CDS': 'http://www.ebi.ac.uk/ena/data/view/{id}',
    'Ensembl': 'http://ensembl.org/Gene/Variation_Gene/Table?g={id}',
    #'Ensembl_PRO':
    #'Ensembl_TRS': 'http://ensembl.org/Transcript/Summary?t={id}',
    'GI': 'http://www.ncbi.nlm.nih.gov/nucleotide/{id}',
    'GeneCards': 'http://www.genecards.org/cgi-bin/carddisp.pl?gene={id}',
    'GeneID': 'http://www.ncbi.nlm.nih.gov/gene?term={id}',
    'GermOnline': 'http://www.germonline.org/Homo_sapiens/geneview?gene={id}',
    'H-InvDB': 'http://h-invitational.jp/hinv/spsoup/locus_view?hix_id={id}',
    'HGNC': 'http://www.genenames.org/data/hgnc_data.php?hgnc_id={id}',
    'HOVERGEN': 'http://pbil.univ-lyon1.fr/cgi-bin/acnuc-dispfam?db=HOVERGEN&query={id}',
    'HPA': 'http://www.proteinatlas.org/search/{id}',
    #'IPI': 
    'KEGG': 'http://www.genome.jp/dbget-bin/www_bget?{id}',
    'KO': 'http://www.genome.jp/dbget-bin/www_bget?ko:{id}',
    'MIM': 'http://omim.org/entry/{id}',
    'MINT': 'http://mint.bio.uniroma2.it/mint/search/search.do?queryType=protein&interactorAc={id}',
    'NCBI_TaxID': 'http://www.ncbi.nlm.nih.gov/taxonomy?term={id}',
    'Orphanet': 'http://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=EN&Expert={id}',
    'PDB': 'http://www.rcsb.org/pdb/explore/explore.do?structureId={id}',
    'PharmGKB': 'http://www.pharmgkb.org/gene/{id}',
    'Reactome': 'http://www.reactome.org/cgi-bin/search2?OPERATOR=ALL&QUERY={id}',
    'RefSeq': 'http://www.ncbi.nlm.nih.gov/entrez/viewer.cgi?val={id}',
    'RefSeq_NT': 'http://www.ncbi.nlm.nih.gov/entrez/viewer.cgi?val={id}',
    'TCDB': 'http://www.tcdb.org/search/result.php?tc={id}',
    'UCSC': 'http://genome.ucsc.edu/cgi-bin/hgGene?hgg_gene={id}',
    'UniGene': 'http://www.ncbi.nlm.nih.gov/unigene?term={id}',
    'UniParc': 'http://www.uniprot.org/uniparc/{id}',
    'UniProtKB-AC': 'http://www.uniprot.org/uniprot/{id}',
    'UniProtKB-ID': 'http://www.uniprot.org/uniprot/{id}',
    'UniRef100': 'http://www.uniprot.org/uniref/{id}',
    'UniRef90': 'http://www.uniprot.org/uniref/{id}',
    'UniRef50': 'http://www.uniprot.org/uniref/{id}',
    'eggNOG': 'http://eggnog.embl.de/version_3.0/cgi/search.py?search_term_0={id}',
    'neXtProt': 'http://www.nextprot.org/db/entry/{id}',
    }

def xreflookup(gene_entrez_id):
    """Look up cross references for a given gene ID from the database"""
    return GeneCrossref.objects.filter(entrez_id=gene_entrez_id).order_by('idtype')


def formatlinks(xrefs):
    """Add a "url" attribute to each item in a list of crossrefs, by formatting
    the appropriate string in the urlformats dict with the crossref ID."""
    
    for xref in xrefs:
        if xref.idtype in urlformats:
            xref.url = urlformats[xref.idtype].format(id=xref.crossref_id)


def groupxrefs(xrefs):
    """Put cross regs into groups with the same id type, to prepare them for
    displaying in the response.  Takes crossrefs (xrefs) as a Django queryset.  
    Return a sorted list of 3-tuples, where the first position is the ID type, 
    the second position is the name to display, and the third position is a list
    of xrefs.  Also add a "url" attribute to each xref."""
    
    xrefgroups = dict()
    for xref in xrefs:
    
        # add url to the 
        #if xref.idtype in urlformats:
        #    xref.url = urlformats[xref.idtype].format(xref.crossref_id)
    
        if xref.idtype in xrefgroups:
            xrefgroups[xref.idtype].append(xref)
        else:
            xrefgroups[xref.idtype] = [xref]
            
    return [(x[0], sourcenames.get(x[0]), x[1]) for x in sorted(xrefgroups.items())]

def groupxrefs2(xrefs):
    
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
    # get gene ID out of query string
    try:
        gene_entrez_id = int(request.GET['gene'])
    except (KeyError, ValueError):
        # error if we don't have a gene ID
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'You need a gene ID to look up crossrefs'}, response)
        return response
    
    # get cross references from database
    xrefs = xreflookup(gene_entrez_id)
    
    # format link URLS
    formatlinks(xrefs)
    
    # put xrefs into groups of ID types
    xrefgroups = groupxrefs(xrefs)
            
    # render and return response
    resulthtml = render_to_string('genecrossrefs.html', {'xrefgroups': xrefgroups})
    response = HttpResponse()
    json.dump({'validresult': True, 'result': resulthtml}, response)
    return response
    
    #return render_to_response('genecrossrefs.html', {'xrefgroups': xrefgroups})
    
def genecrossrefs2(request):
    # get gene ID out of query string
    try:
        gene_entrez_id = int(request.GET['gene'])
    except (KeyError, ValueError):
        # error if we don't have a gene ID
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'You need a gene ID to look up crossrefs'}, response)
        return response
    
    # get cross references from database
    xrefs = xreflookup(gene_entrez_id)
    
    # format link URLS
    formatlinks(xrefs)
    
    # put xrefs into groups of ID types
    xrefcats = groupxrefs2(xrefs)
            
    # render and return response
    resulthtml = render_to_string('genecrossrefs2.html', {'xrefcats': xrefcats})
    response = HttpResponse()
    json.dump({'validresult': True, 'result': resulthtml}, response)
    return response
    
    #return render_to_response('genecrossrefs.html', {'xrefgroups': xrefgroups})
