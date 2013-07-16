"""
to-do's

maximum number of genes in a file?
maximum file size?
mechanism to keep people from looking at other people's files?
remember files that people have already uploaded in a session?
check species of genes?

"""

import json

from django.template.loader import render_to_string
from django import forms
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from genetext.geneindex.models import Gene, UploadedGeneFile, UploadedGene

class BadGeneError(Exception):
    """Exception to raise if an ID in a file can't be matched to a gene"""
    pass


def loadfile(file):
    """Load a file of Entrez Gene ID's into the database.   Returns the file
    ID of the file.  Raise an exception if one of the ID's isn't in the gene 
    index."""

    # load the ID's in the file into a set
    genes = set()
    for line in file:
        # turn the line into an int
        try:
            g = int(line)
        except ValueError:
            raise BadGeneError(line.strip())

        # make sure that the gene is in our database
        if not Gene.objects.get(pk=g):
            raise BadGeneError(line.strip())

        # add the gene to the set of genes
        genes.add(g)

    # create a new genefile entry in the database
    gf = UploadedGeneFile(name=file.name)
    gf.save()

    # insert each gene into the database
    for g in genes:
        ug = UploadedGene(genefile=gf, gene=g)
        print ug.genefile
        ug.save()

    file.close()

    # return the file id and name
    return gf.id, gf.name


class GeneFileForm(forms.Form):
    genefile = forms.FileField(label="Gene file")


@csrf_exempt # this is okay because we don't have user accounts
def uploadpage(request):
    """Little web page with a form to upload a gene file"""

    if request.method == 'POST':
        form = GeneFileForm(request.POST, request.FILES)
        message = ""
        print('debug 1')
        if form.is_valid():
            print('debug 2')
            try:
                fileID, filename = loadfile(request.FILES['genefile'])
                

                response = HttpResponse()
                json.dump({'success': True, 'page': None}, response)
                response.set_cookie('genefileID', fileID)
                response.set_cookie('genefilename', filename)
                return response


            except BadGeneError as err:
                message = 'Gene ID not in our database: ' + str(err.args[0])


    else:
        message = "no file yet!"
        form = GeneFileForm()

    formpage = render_to_string('genefileupload.html', 
        {'form':form, 'message':message})
    response = HttpResponse()
    json.dump({'success': False, 'page': formpage}, response)
    return response
