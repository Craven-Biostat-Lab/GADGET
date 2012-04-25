import json
from django.http import HttpResponse
from django.template.loader import render_to_string
from genetext.geneview.models import GeneCrossref

from django.shortcuts import render_to_response

# hard code database names and urls
sourcenames = {
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
    return GeneCrossref.objects.filter(entrez_id=gene_entrez_id)


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
