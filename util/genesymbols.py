#!/usr/bin/python
"""
Create a table linking gene symbols to genes, using a table with HUGO data.
(Use to create a dictionary for named entity recognition)
"""

import MySQLdb as m

db = m.connect(user='root', passwd='password', db='genetext')
c = db.cursor()

c.execute("""DROP TABLE IF EXISTS `gene_symbol`;""")
c.execute("""
    CREATE TABLE `gene_symbol` (
    `hugo` INT  NOT NULL,
    `symbol` VARCHAR(200)  NOT NULL
    )
    ENGINE = MyISAM;
    """)
c.execute("""
    SELECT hugo, symbol, name, old_symbols, aliases
    from gene_raw;
    """)

for gene in c.fetchall():
    syms = [gene[1], gene[2]]
    syms.extend([g.strip() for g in gene[3].split(',')])
    syms.extend([g.strip() for g in gene[4].split(',')])
    c.executemany(
    """
    INSERT INTO `gene_symbol` (hugo, symbol)
    VALUES ({0}, %s);
    """.format(gene[0]), syms)

c.close()
db.close()
