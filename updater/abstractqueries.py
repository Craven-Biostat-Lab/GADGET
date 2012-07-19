#!/usr/bin/python

# set up logging
import logging
logger = logging.getLogger('GADGET.updater.abstractqueries')


def getcursor(db):
    """Create and return a cursor from the database connection"""
    
    try:
        c = db.cursor()
        c.execute('SET NAMES utf8;')
        c.execute('SET CHARACTER SET utf8;')
        c.execute('SET character_set_connection=utf8;')
    except Exception as e:
        logger.critical('Error creating database cursor.  Error message: %s', e)
        raise

    return c


def add_new_abstracts(db):
    """Add abstracts from the 'gene_abstract' link table to the 'abstract'
    table."""

    logger.debug('adding abstract id\'s from gene_abstract table to the abstract table')

    c = getcursor(db)

    try:
        c.execute("""
        insert ignore into `abstract` (`pubmed_id`)
        select distinct `abstract` from `gene_abstract`; 
        """)
    except Exception as e:
        logger.critical('Error inserting add new abstract ID\'s from gene-abstract links into abstract table.  Error message: %s', e)
        raise

    c.close()
    logger.info('added new abstract ID\'s to abstract table')    


def find_too_many_genes(db, maxgenes=1000):
    """Find abstracts with more than 'maxgenes' (1000 by default) associated 
    genes, and then add them to the 'removed_abstracts' table to get rid of 
    GWA papers"""

    logger.debug('adding abstracts to `removed_abstracts` table with too many (> %s) associated genes', maxgenes)

    c = getcursor(db)

    try:
        c.execute("""
        insert ignore into `removed_abstracts`
        (`abstract`, `removed`, `reason`)
        select `abstract`, now() `removed`, 1 `reason`
        from `gene_abstract`
        group by `abstract`
        having count(`gene`) > %s
        """, (maxgenes,))
    except Exception as e:
        logger.critical('Error adding abstracts with too many genes (> %s) to `removed_abstracts` table.  Error message: %s', maxgenes, e)
        raise

    c.close()
    logger.info('added abstracts to `removed_abstracts` table with too many (> %s) associated genes', maxgenes)


def remove_bad_abstracts(db):
    """Remove abstracts in the 'removed_abstracts' table from the 'abstract' table"""

    logger.debug('removing abstracts in the `removed_abstracts` table from the `abstract` table')

    c = getcursor(db)

    try:
        c.execute("""
        delete `abstract`
        from `abstract`
        inner join `removed_abstracts`
        on `abstract`.`pubmed_id` = `removed_abstracts`.`abstract`
        """)
    except Exception as e:
        logger.critical('Error removing abstracts in the `removed_abstracts` table from the `abstract` table.  Error message: %s', e)
        raise

    c.close()
    logger.info('removed abstracts in the `removed_abstracts` table from the `abstract` table')


def find_unfetched_abstracts(db):
    """Find unfetched abstracts in the `abstract` table (where the `abstract`
    field is null,) and add them to the `removed_abstracts` table"""

    logger.debug('Finding unfetched abstracts in the `abstract` table (where the `abstract` field is null), and adding them to the `removed_abstract` table')

    c = getcursor(db)

    try:
        c.execute("""
        insert ignore into `removed_abstracts`
        (`abstract`, `removed`, `reason`)
        select `pubmed_id` `abstract`, now() `removed`, 2 `reason`
        from `abstract` a
        where a.`abstract` is null""")
    except Exception as e:
        logger.critical('Error adding unfetched abstracts to `removed_abstract` table.  Error message: %s', e)
        raise

    c.close()
    logger.info('Found unfetched abstracts in the `abstract` table (where the `abstract` field is null), and added them to the `removed_abstract` table')


def remove_bad_links(db):
    """Remove `gene_abstract` links for abstracts not in the `abstract` table"""

    logger.debug('Removing `gene_abstract` links for abstracts not in the `abstract` table')

    c = getcursor(db)

    try:
        c.execute("""
        delete `gene_abstract`
        from `gene_abstract`
        left join `abstract`
        on `gene_abstract`.`abstract` = `abstract`.`pubmed_id`
        where `abstract`.`pubmed_id` is null""")
    except Exception as e:
        logger.critical('Error removing `gene_abstract` links for abstracts not in the `abstract` table.  Error message: %s', e)
        raise

    c.close()
    logger.info('Removed `gene_abstract` links for abstracts not in the `abstract` table')


def make_homolog_links(db):
    """Add gene_abstract links for homologs (using homologene_gene table)"""

    logger.debug('inserting records from `gene_abstract` into `homologene_gene_abstract` table')

    c = getcursor(db)

    try:
        c.execute("""
        insert ignore into `homologene_gene_abstract`
        select * from `gene_abstract`
        """)
    except Exception as e:
        logger.critical('Could not insert records from `gene_abstract` into `homologene_gene_abstract` table.  Error message: %s', e)
        raise

    logger.debug('inserting homolog links from `gene_abstract` and `homologene_gene` into `homologene_gene_abstract`')
    try:
        c.execute("""
        insert ignore into `homologene_gene_abstract`
        select null `id`, h1.`gene` `gene`, ga.`abstract` `abstract`
        from `homologene_gene` h1
        inner join `homologene_gene` h2 on h1.`homologene_id` = h2.`homologene_id`
        inner join `gene_abstract` ga on h2.`gene` = ga.`gene`
        """)
    except Exception as e:
        logger.critical('could not insert homolog links from `gene_abstract` and `homologene_gene` into `homologene_gene_abstract`.  Error message: e', e)
        raise

    c.close()
    logger.info('inserted records from `gene_abstract` into `homologene_gene_abstract` table')


def count_genes(db):
    """Update the `gene` table with counts of associated abstracts"""

    logger.debug('updating the `gene` table with new abstract counts')

    c = getcursor(db)

    try:
        c.execute("""
        update `gene`
        set `gene`.`abstracts` = (
            select count(distinct `abstract`) 
            from `gene_abstract` 
            where `gene_abstract`.`gene` = `gene`.`entrez_id`),
        `gene`.`homolog_abstracts` = (
            select count(distinct `abstract`) 
            from `homologene_gene_abstract` 
            where `homologene_gene_abstract`.`gene` = `gene`.`entrez_id`);
        """)
    except Exception as e:
        logger.critical('Error updating the `gene` table with new abstract counts.  Error message: %s', e)
        raise

    c.close()
    logger.info('updated the `gene` table with new abstract counts')
