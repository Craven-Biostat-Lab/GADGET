from django.db import models

class Gene(models.Model):
    tax_id = models.IntegerField()
    entrez_id = models.IntegerField(primary_key=True)
    symbol = models.CharField(max_length=30)
    locustag = models.CharField(max_length=100)
    synonyms = models.CharField(max_length=250)
    description = models.CharField(max_length=250)
    chromosome = models.CharField(max_length=7)
    maplocation = models.CharField(max_length=100)
    abstracts = models.IntegerField()

    def __unicode__(self):
        return self.symbol

    class Meta:
        db_table = 'gene'
        managed = False
        
class Abstract(models.Model):
    pubmed_id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=900, blank=True)
    authors = models.CharField(max_length=900, blank=True)
    year = models.IntegerField(null=True, blank=True)
    month = models.CharField(max_length=9, blank=True)
    journal = models.CharField(max_length=450, blank=True)
    volume = models.IntegerField(null=True, blank=True)
    issue = models.IntegerField(null=True, blank=True)
    pages = models.CharField(max_length=90, blank=True)
    
    class Meta:
        db_table = u'abstract'
        managed = False
        
class GeneAbstract(models.Model):
    id = models.IntegerField(primary_key=True)
    gene = models.ForeignKey(Gene, db_column='gene')
    abstract = models.ForeignKey(Abstract, db_column='abstract_pmid')
    
    class Meta:
        db_table = 'gene_abstract'
        managed = False
        
class GeneCrossref(models.Model):
    id = models.IntegerField(primary_key=True)
    entrez_id = models.IntegerField()
    idtype = models.CharField(max_length=20)
    crossref_id = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'gene_crossrefs'
        managed = False
