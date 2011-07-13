from django.db import models

class Gene(models.Model):
    id = models.IntegerField(primary_key=True)
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    old_symbols = models.CharField(max_length=150)
    aliases = models.CharField(max_length=150)
    chromosome = models.CharField(max_length=50)
    accession = models.CharField(max_length=100)
    entrez = models.IntegerField()
    hugo = models.IntegerField()
    refseq = models.CharField(max_length=50)
    uniprot = models.CharField(max_length=10)

    def __unicode__(self):
        return self.symbol

    class Meta:
        db_table = 'gene'
        managed = False

class Word(models.Model):
    id = models.IntegerField(primary_key=True)
    word = models.CharField(max_length=50)

    class Meta:
        db_table = 'word'
        managed = False

class GeneWord(models.Model):
    id = models.IntegerField(primary_key=True)
    gene = models.ForeignKey(Gene)
    word = models.ForeignKey(Word)
    weight = models.FloatField()

    class Meta:
        db_table = 'gene_word'
        managed = False
