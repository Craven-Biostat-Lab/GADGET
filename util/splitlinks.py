#!/usr/bin/python

"""Parse datbase crosslinks in the `dbxrefs` field of the `gene` table, and put
them into separate hgnc_id, mim_id, ensembl_id, and hprd_id fields."""

import MySQLdb
import re

hgnc_pattern = re.compile(r'HGNC:([0-9]+)')
mim_pattern = re.compile(r'MIM:([0-9]+)')
ensembl_pattern = re.compile(r'Ensembl:ENSG([0-9]+)')
hprd_pattern = re.compile(r'HPRD:([0-9]+)')

# connect to database
db = MySQLdb.connect(user='root', passwd='password', db='genetext')
c = db.cursor()

# get genes without split dbxrefs
c.execute("""
    SELECT `id`, `dbxrefs`
    FROM `gene`
    WHERE `dbxrefs_split` = 0;
    """)

# for each gene
for id, dbxrefs in c.fetchall():
    # parse out database ID's
    hgnc_match = hgnc_pattern.search(dbxrefs)
    mim_match = mim_pattern.search(dbxrefs)
    ensembl_match = ensembl_pattern.search(dbxrefs)
    hprd_match = hprd_pattern.search(dbxrefs)
    
    hgnc_id = hgnc_match and int(hgnc_match.groups()[0]) or None
    mim_id = mim_match and int(mim_match.groups()[0]) or None
    ensembl_id = ensembl_match and int(ensembl_match.groups()[0]) or None
    hprd_id = hprd_match and int(hprd_match.groups()[0]) or None
    
    # update gene table
    c.execute("""UPDATE `gene` set 
        `hgnc_id` = %(hgnc_id)s, 
        `mim_id` = %(mim_id)s, 
        `ensembl_id` = %(ensembl_id)s, 
        `hprd_id` = %(hprd_id)s,
        `dbxrefs_split` = 1
        WHERE `id` = %(id)s""", locals())
        
c.close()
