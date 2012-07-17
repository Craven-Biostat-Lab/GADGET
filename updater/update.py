import load_gene_abstract_links 
import abstractqueries
import fetchabstracts

#TODO: set up logging

if __name__ == '__main__':
    
    # 1: get new gene_abstract links from gene2pubmed, MGI, SGD, etc.
    load_gene_abstract_links.loadall()
    load_gene_abstract_links.cleanup()

    # 2: 'mark dirty abstracts' trigger set 'dirty_indexed' column to now()
    # for abstracts with new gene-abstract links

    # 3: add new abstracts from 'gene_abstract' links to 'abstract' table
    abstractqueries.add_new_abstracts()

    # 4: add abstracts with more than 1000 genes to 'removed_abstract' table
    abstractqueries.find_too_many_abstracts()

    # 5: remove abstracts in 'removed_abstract' table from 'abstract' table
    abstractqueries.remove_bad_abstracts()

    # 6: fetch new abstracts from PubMed
    fetchabstracts.fetchall()

    # 7: add abstracts that couldn't be fetched to 'removed_abstract' table
    abstractqueries.find_unfetched_abstracts()

    # 8: remove abstracts in 'removed_abstract' table from 'abstract' table
    abstractqueries.remove_bad_abstracts()

    # 9: remove 'gene_abstract' links for abstracts not in 'abstract' table
    abstractqueries.remove_bad_links()

    # 10: update abstract index - add new abstracts and "index_dirty" abstracts
    # TODO

    # 11: update 'gene' table, count abstracts for each gene
    # TODO
