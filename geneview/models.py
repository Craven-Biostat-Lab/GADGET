from django.db import models

class Gene(models.Model):
    id = models.IntegerField(primary_key=True)
    symbol = models.CharField(max_length=30)
    name = models.CharField(max_length=250)
    locustag = models.CharField(max_length=100)
    synonyms = models.CharField(max_length=250)
    
    entrez_id = models.IntegerField()
    hgnc_id = models.IntegerField()
    mim_id = models.IntegerField()
    ensembl_id = models.IntegerField()
    hprd_id = models.IntegerField()
    
    chromosome = models.CharField(max_length=7)
    maplocation = models.CharField(max_length=100)
    genetype = models.CharField(max_length=20, db_column='type') # 'type' means something in python
    other = models.TextField()
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
        db_table = u'abstract_info'
        managed = False
        
class GeneAbstract(models.Model):
    id = models.IntegerField(primary_key=True)
    gene = models.ForeignKey(Gene, db_column='gene')
    abstract = models.ForeignKey(Abstract, db_column='abstract_pmid')
    
    class Meta:
        db_table = 'gene_abstract'
        managed = False