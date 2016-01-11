from django.db import models


        
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
        
class Metabolite(models.Model):
    hmdb_id = models.CharField(primary_key=True, max_length=30)
    common_name = models.CharField(max_length=250)
    synonyms = models.TextField(blank=True)
    abstracts = models.IntegerField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'metabolite'
        
    def synonyms_list(self):
        return self.synonyms.split('\n')

class MetaboliteAbstract(models.Model):
    id = models.IntegerField(primary_key=True)
    metabolite_hmdb_id = models.CharField(max_length=30)
    abstract = models.IntegerField()
    class Meta:
        managed = False
        db_table = 'metabolite_abstract'

        

