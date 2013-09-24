#!/usr/bin/python
"""
Delete uploaded gene files that are more than a day old from the database.
"""

from config import getcursor

import logging
logger = logging.getLogger('GADGET.updater.clearuploadedfiles')

def clearfiles(db):

    logger.debug('Deleting uploaded files more than 1 day old from database')

    c.getcursor(db)

    # delete uploaded genes and uploaded files more than a day old
    c.execute("""
    delete uploaded_gene, uploaded_genefile 
    from uploaded_gene
    inner join uploaded_genefile
    on uploaded_gene.`genefile` = uploaded_genefile.`id`
    where uploaded_genefile.`uploaded` > (now() - interval 1 day);
    """)

    # delete uploaded files with no genes
    c.execute("""
    delete uploaded_genefile
    from uploaded_genefile
    left join uploaded_gene
    on uploaded_gene.genefile = uploaded_genefile.id
    where uploaded_gene.`genefile` is null;    
    """)

    # delete uploaded genes with no file
    c.execute("""
    delete uploaded_gene
    from uploaded_gene
    left join uploaded_genefile
    on uploaded_gene.genefile = uploaded_genefile.id
    where uploaded_genefile.`id` is null;
    """)

    c.close()

    logger.info('Finished deleting old files')
