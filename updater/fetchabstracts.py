#!/usr/bin/python
"""
Grab Pubmed ID's for records with no titles in a database table of articles, and
look up and fill in metadata using entrez.
"""

import urllib
import MySQLdb
from xml.etree import ElementTree as ET

from config import getcursor, abstracturl, abstract_fetch_batchsize

# set up logging
import logging
logger = logging.getLogger('GADGET.updater.fetchabstracts')


def convertmonth(m):
    """Months are stored in PubMed in a couple different forms.
    Convert them all to numeric representations (return a string.)"""
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    if m is None: return '0'
    elif m.isdigit(): return m
    elif m.lower() in months: return str(months.index(m.lower()) + 1)
    else:
        print 'invalid month:', m
        return '0'


def fetch(idlist):
    """Fetch and return metadata for a list of Pubmed IDs.  Returns a lists of 
    dicts, each dict containing data for one abstract."""
        
    # fetch from entrez
    idstring = ','.join([str(i) for i in idlist])

    try:
        u = urllib.urlopen(abstracturl.format(idstring))
    except Exception as e:
        logger.error('Error fetching abstracts from PubMed.  url: %s    Error message: %s', abstracturl.format(idstring), e)
        raise
    
    try:
        root = ET.parse(u, parser=ET.XMLParser(encoding='utf-8')).getroot()
    except Exception as e:
        logger.error('Error parsing abstract XML from PubMed: %s', e)
        raise
    
    u.close()
    
    # parse XML for each abstract
    results = []
    for artroot in root.findall('PubmedArticle'):
        art = artroot.find('MedlineCitation').find('Article')
        
        def get(*path, **kwargs):
            """Get attributes out of the XML, fail gracefully when we can't find it."""
            try:
                n = art
                for p in path:
                    n = n.find(p)
                return n.text.encode('utf-8')
            except AttributeError:
                return kwargs.get('default')
            
        id = int(artroot.find('MedlineCitation').find('PMID').text)
        
        # journal
        journal = get('Journal', 'Title') #
        volume = get('Journal', 'JournalIssue', 'Volume') #
        issue = get('Journal', 'JournalIssue', 'Issue') #
        year = get('Journal', 'JournalIssue', 'PubDate', 'Year', default='0') #
        month = convertmonth(get('Journal', 'JournalIssue', 'PubDate', 'Month')) #
        day = get('Journal', 'JournalIssue', 'PubDate', 'Day', default='0')
        
        # article
        title = get('ArticleTitle', default='')
        pages = get('Pagination', 'MedlinePgn')
        abstract = get('Abstract', 'AbstractText')
        
        # figure out if this article is a review
        try:
            review = 'review' in [pt.text.lower() for pt in art.find('PublicationTypeList').findall('PublicationType')]
        except AttributeError:
            review = False

        try:
            # author list (concatenate into a string)
            authors = u', '.join([
                u" ".join((a.find('LastName').text, a.find('ForeName').text)) 
                for a in art.find('AuthorList') ]).encode('utf-8') #
        except (AttributeError, TypeError):
            authors = None
        
        results.append(dict(
            id=id,
            journal=journal,
            volume=volume,
            issue=issue,
            year=year,
            month=month,
            day=day,
            title=title,
            pages=pages,
            abstract=abstract,
            review=review,
            authors=authors))

    return results


def ids(db, size = abstract_fetch_batchsize):
    """Find all pubmed ID's of abstracts with `updated` set to null.  Return an
    iterator over lists of abstract PMID's with the given size (for fetching
    multiple abstracts at once.)"""

    logger.debug('Quering database for a list of un-fetched abstracts')

    c = getcursor(db)

    try:
        c.execute("""
            select `pubmed_id`
            from `abstract`
            where `updated` is null;
        """)
    except Exception as e:
        logger.critical('Error: could not get a list of un-fetched abstracts from the database.  Error message: %s', e)
        raise
    
    logger.info('Got list of un-fetched abstracts')

    records = c.fetchall()
    c.close()

    for i in xrange(0, len(records), size):
        yield [r[0] for r in records[i:i+size]]


def update(db, metadata):
    """Enter metadata into the table using a given list of dicts.  Each dict is
    one row."""
   
    c = getcursor(db)

    for m in metadata:
        try:
            c.execute("""
                update `abstract`
                set title := %s,
                authors := %s,
                abstract := %s,
                pubdate := %s,
                journal := %s,
                volume := %s,
                issue := %s,
                pages := %s,
                review := %s,
                updated := now()
                where pubmed_id = %s;
            """,
            (m['title'], m['authors'], m['abstract'], (m['year'] +'-'+ m['month'] +'-'+m['day']), 
            m['journal'], m['volume'], m['issue'], m['pages'], m['review'], m['id'])
            )
        except Exception as e:     
            logger.error('Error updating `abstract` table for PMID %s.  Error message: %s', m['id'], e)

    c.close()


def fetchall(db):
    """Find all un-fetched abstracts in the 'abstract' table, and fetch them
    from PubMed"""

    logging.debug('Fetching unfetched abstracts in `abstract` table')
    
    for idlist in ids(db):
        try:
            m = fetch(idlist)
            update(db, m)
        except Exception as e:
            logger.Error('Exception while fetching abstracts from pubmed.  IDlist: %s,   error message: %s', idlist, e)

    logger.info('Fetched unfetched abstracts in `abstract` table')


if __name__ == '__main__':
    fetchall()
