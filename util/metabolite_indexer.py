
#import MySQLdb
import atexit
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, DATETIME, STORED, BOOLEAN
from whoosh.qparser import MultifieldParser, QueryParser, PhrasePlugin
from whoosh.query import And, Or, Term, ConstantScoreQuery, NullQuery, Query
from whoosh.scoring import BM25F
from whoosh.sorting import MultiFacet
from datetime import datetime





ABSTRACT_INDEX_PATH = './abstracts' #THIS IS WHAT NEEDS TO BE CHANGED, TO CURRENT ABSTRACT WHOOSH INDEX


#Check if Index exists and if not create it (should always exist)
if index.exists_in(ABSTRACT_INDEX_PATH):
    ix = index.open_dir(ABSTRACT_INDEX_PATH)
else:
    # define the index fields
    class Schema(SchemaClass):
        pmid = NUMERIC(stored=True, unique=True, signed=False)
        genes = IDLIST(stored=True) # Entrez ID's
        homolog_genes = IDLIST(stored=True) # Entrez ID's
        title = TEXT(stored=True)
        abstract = TEXT
        authors = TEXT(stored=True)
        year = NUMERIC(stored=True)
        month = NUMERIC(stored=True)
        day = NUMERIC(stored=True)
        review = BOOLEAN(stored=True)
        journal = STORED
        volume = STORED
        pages = STORED
        
    ix = index.create_in(ABSTRACT_INDEX_PATH, Schema)


# query parser and searcher
parser = QueryParser('abstract',ix.schema)
parser.add_plugin(PhrasePlugin)
searcher = ix.searcher(weighting=BM25F)


# facet object for sorting abstracts by date (some have years but not dates)
datefacet = MultiFacet()
datefacet.add_field('year')
datefacet.add_field('month')
datefacet.add_field('day')


#Builds Query
def buildquery(keywords=None):
    # get keyword branch of query
    print "keywords (buildquery input) ==", keywords
    keywords = keywords.decode("utf-8")
    

    #print "Keyword in Unicode ==", unicode(keywords)
    keywordbranch = parser.parse(unicode(keywords)) if keywords else NullQuery()
    #print "keywordbranch (buildquery, pre-score) ==", keywordbranch
    #print ""

    return ConstantScoreQuery(keywordbranch)

#Retrieve abstracts
def get_abstracts(keywords=None):
    query = buildquery(keywords)
    print "Query ==", query
    results = [r['pmid'] for r in searcher.search(query, limit=None)]
    return results



#Get all common names so they don't repeat
outfile = open('metabolite2pubmed.txt','w') #mapping file
common_name_set = set()
with open('metabolite_info.txt')as f:
    for line in f:
        if line.startswith('HMDB'):
            synonym_line=f.next().strip()
            synonyms = synonym_line.split('\t')
            common_name = synonyms[0]
            print(common_name)
            common_name_set.add(common_name)


#search abstracts and write to metabolite2pubmed.txt
with open('metabolite_info.txt') as f:
    for line in f:
        if line.startswith('HMDB'):
            outfile.write(line) #Write ID to file (line 1)
            synonym_line = f.next().strip()
            #outfile.write(synonym_line)
            synonyms = synonym_line.split('\t')
            common_name = synonyms[0]
            printsyn = common_name + '\t'
            for s in synonyms:
                if s in common_name_set and s != common_name:
                    synonyms.remove(s)
                    continue
                if s == common_name:
                    continue
                printsyn = printsyn + '\t' +s
            outfile.write(printsyn+'\n') #Write synonyms to file (line 2)
            reference_line = f.next().strip()
            references = set(reference_line.split('\t'))
            if '\n' in references:
                references.remove('\n')

            for name in synonyms:
                query = '"' + name + '"' #performs complete query
                results = get_abstracts(query) #searches with get_abstracts useing "line" as the search keyword
                for item in results:
                    references.add(str(item))


            rlist = list(references)
            rline = '\t'.join(references) + '\n'
            outfile.write(rline) #Write references to file (line 3)


outfile.close()


    
   

        

