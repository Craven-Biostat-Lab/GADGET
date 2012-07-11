create trigger `mark_dirty_abstracts`
after insert on `gene_abstract`
for each row
update `abstract` a
set a.`index_dirty` = now()
where a.`pubmed_id` = new.`abstract_pmid`
and new.`gene` != 0;
