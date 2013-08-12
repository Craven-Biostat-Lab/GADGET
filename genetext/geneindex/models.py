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


class UploadedGeneFile(models.Model):
    id = models.AutoField(primary_key=True) 
    name = models.CharField(max_length=100)
    uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_genefile'
        managed = False


class UploadedGene(models.Model):
    id = models.AutoField(primary_key=True)
    genefile = models.ForeignKey(UploadedGeneFile, db_column="genefile")
    gene = models.IntegerField(Gene, db_column="entrez_gene_id")

    class Meta:
        db_table = 'uploaded_gene'
        managed = False
