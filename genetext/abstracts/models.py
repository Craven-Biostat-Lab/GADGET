from django.db import models
        
class KeyPhrase(models.Model):
    id = models.IntegerField(primary_key=True)
    numtokens = models.IntegerField(null=True, blank=True)
    string = models.CharField(max_length=200, blank=True)
    abstractcount = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = u'keyphrase'
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
        
        
class KeyphraseAbstract(models.Model):
    id = models.IntegerField(primary_key=True)
    keyphrase = models.ForeignKey(KeyPhrase, db_column='keyphrase', related_name='ka_keyphrase')
    abstract = models.ForeignKey(Abstract, db_column='abstract', related_name='ka_abstract')
    
    class Meta:
        db_table = u'keyphrase_abstract'
        managed = False