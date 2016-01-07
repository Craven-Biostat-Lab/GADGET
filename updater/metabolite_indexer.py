"""
Scans new articles for metabolites, and updates the metabolite_abstract database
table.
"""



#import MySQLdb
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, DATETIME, STORED, BOOLEAN
from whoosh.qparser import MultifieldParser, QueryParser, PhrasePlugin
from whoosh.query import And, Or, Term, ConstantScoreQuery, NullQuery, Query
from whoosh.scoring import BM25F
from whoosh.sorting import MultiFacet
from datetime import datetime


from config import TEMP_METABOLITE_INDEX_PATH, getcursor
from buildindex import open_index


# set up logging
import logging
logger = logging.getLogger('GADGET.updater.metabolite_indexer')



#Builds Query
def buildquery(parser, keywords=None):
    # get keyword branch of query
    #print "keywords (buildquery input) ==", keywords
    keywords = keywords.decode("utf-8")
    

    #print "Keyword in Unicode ==", unicode(keywords)
    keywordbranch = parser.parse(unicode(keywords)) if keywords else NullQuery()
    #print "keywordbranch (buildquery, pre-score) ==", keywordbranch
    #print ""

    return ConstantScoreQuery(keywordbranch)

#Retrieve abstracts
def get_abstracts(parser, searcher, keywords=None):
    query = buildquery(parser, keywords)
    #print "Query ==", query
    results = [r['pmid'] for r in searcher.search(query, limit=None)]
    return results






def insert_db_records(cursor, hmdb_id, abstracts):
    """
    Insert a metabolite-abstract link into the database.
    """
    
    for a in abstracts:
        cursor.execute(
        """
            INSERT IGNORE INTO `metabolite_abstract`
            (`metabolite_hmdb_id`, `abstract`)
            VALUES
            (%s, %s)
        """, 
        [hmdb_id, a])





def update_metabolites(db):
    """
    Find metabolites mentioned in new articles, and insert new records into the
    metabolite_abstract table in the database.
    
    (For each metabolite in the metabolite_info.txt file, search against the 
    temporary whoosh index containing only new articles.)
    """

    logger.debug('Scanning for metabolites')

    # Don't open the index until this enclosing function is called, because
    # we'll be deleting it and re-creating it in a previous state of the 
    # update process.
    ix = open_index(TEMP_METABOLITE_INDEX_PATH)
    cursor = getcursor(db)


    # query parser and searcher
    parser = QueryParser('abstract',ix.schema)
    parser.add_plugin(PhrasePlugin)
    searcher = ix.searcher(weighting=BM25F)


    #Get all common names so they don't repeat
    #outfile = open('metabolite2pubmed.txt','w') #mapping file
    common_name_set = set()
    with open('metabolite_info.txt')as f:
        for line in f:
            if line.startswith('HMDB'):
                synonym_line=f.next().strip()
                synonyms = synonym_line.split('\t')
                common_name = synonyms[0]
                #print(common_name)
                common_name_set.add(common_name)


    #search abstracts and write to metabolite2pubmed.txt
    with open('metabolite_info.txt') as f:
        for line in f:
            if line.startswith('HMDB'):
                #outfile.write(line) #Write ID to file (line 1)
                
                hmdb_id = line.strip()
                
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
                #outfile.write(printsyn+'\n') #Write synonyms to file (line 2)
                reference_line = f.next().strip()
                references = set(reference_line.split('\t'))
                if '\n' in references:
                    references.remove('\n')

                for name in synonyms:
                    query = '"' + name + '"' #performs complete query
                    results = get_abstracts(parser, searcher, query) #searches with get_abstracts useing "line" as the search keyword
                    for item in results:
                        references.add(str(item))


                rlist = list(references)
                
                insert_db_records(cursor, hmdb_id, rlist)
                
                #rline = '\t'.join(references) + '\n'
                #outfile.write(rline) #Write references to file (line 3)


    logger.info('updated metabolite-abstract links')


        
       

            

