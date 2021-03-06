from django.db import models

class Abstract(models.Model):
    pubmed_id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=900, blank=True)
    authors = models.CharField(max_length=900, blank=True)
    pubdate = models.DateField(blank=True)
    journal = models.CharField(max_length=450, blank=True)
    volume = models.IntegerField(null=True, blank=True)
    issue = models.IntegerField(null=True, blank=True)
    pages = models.CharField(max_length=90, blank=True)
    review = models.BooleanField(blank=True)
    
    def year(self):
        try:
            return self.pubdate.year
        except AttributeError:
            return None

    class Meta:
        db_table = u'abstract'
        managed = False

class Gene(models.Model):
    id = models.IntegerField(primary_key=True)
    entrez_id = models.IntegerField(null=True, blank=True)
    symbol = models.CharField(max_length=90, blank=True)
    name = models.CharField(max_length=750, blank=True)
    locustag = models.CharField(max_length=300, blank=True)
    synonyms = models.CharField(max_length=750, blank=True)
    hgnc_id = models.IntegerField(null=True, blank=True)
    mim_id = models.IntegerField(null=True, blank=True)
    ensembl_id = models.IntegerField(null=True, blank=True)
    hprd_id = models.IntegerField(null=True, blank=True)
    chromosome = models.CharField(max_length=21, blank=True)
    maplocation = models.CharField(max_length=300, blank=True)
    abstracts = models.BigIntegerField()
    
    class Meta:
        db_table = u'gene_old'
        managed = False

class Event(models.Model):
    id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=57)
    eventstructure = models.ManyToManyField('self', through='EventEvent', symmetrical=False, related_name='reverse_eventstructure')
    rootstructure = models.ManyToManyField('self', through='EventRoot', symmetrical=False, related_name='reverse_rootstructure')
    abstracts = models.ManyToManyField(Abstract, through='EventAbstract')
    genes = models.ManyToManyField(Gene, through='EventGene')
    
    class Meta:
        db_table = u'event'
        managed = False

class EventAbstract(models.Model):
    id = models.IntegerField(primary_key=True)
    event = models.ForeignKey(Event, db_column='event')
    abstract_pmid = models.ForeignKey(Abstract, db_column='abstract_pmid')
    confidence_min = models.FloatField(null=True, blank=True)
    
    class Meta:
        db_table = u'event_abstract'
        managed = False

class EventEvent(models.Model):
    parent = models.ForeignKey(Event, primary_key=True, db_column='parent', related_name='children')
    child = models.ForeignKey(Event, primary_key=True, db_column='child', related_name='parents')
    role = models.CharField(max_length=15, primary_key=True)
    
    class Meta:
        db_table = u'event_event'
        managed = False

class EventRoot(models.Model):
    root = models.ForeignKey(Event, primary_key=True, db_column='root', related_name='allchildren')
    event = models.ForeignKey(Event, primary_key=True, db_column='event', related_name='roots')
    
    class Meta:
        db_table = u'event_root'
        managed = False

class EventGene(models.Model):
    id = models.IntegerField(primary_key=True)
    gene = models.ForeignKey(Gene, db_column='gene')
    homologene_id = models.IntegerField()
    event = models.ForeignKey(Event, db_column='event')
    # take out "root" because Django can only handle m2m relationships with one foreign key to each table
    # root = models.ForeignKey(Event, db_column='root', null=True, blank=True, related_name='root')
    role = models.CharField(max_length=15)
    
    class Meta:
        db_table = u'event_gene'
        managed = False

