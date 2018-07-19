#!/usr/bin/python
"""Merge the segments of the abstract index into one segment for faster
searching.  This will take a long time.  If the index is updated nightly,
run this about once a week."""
import buildindex
from config import ABSTRACT_INDEX_PATH

#used to delay start for crontab job
import time
time.sleep(172800) # sleep for 2 days before starting
# set up logging
import logging
logger = logging.getLogger('GADGET.updater.mergeindex')

def merge(ix):
    Merge all index segments for faster queries.
    This will take a long time.

    logger.debug('merging index segments')
    writer = ix.writer()
    writer.commit(optimize=True)
    logger.info('merged index segments')


if __name__ == '__main__':
    
    try:
        ix = buildindex.open_index(ABSTRACT_INDEX_PATH)
    except Exception as e:
        logger.error('could not open index to merge.  Error message: %s', e)
        raise

    try:
        merge(ix)
    except Exception as e:
        logger.error('could not merge index.  Error message: %s', e)
        raise


