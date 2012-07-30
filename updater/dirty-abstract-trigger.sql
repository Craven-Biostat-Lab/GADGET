create trigger `mark_dirty_abstracts`
after insert on `gene_abstract`
for each row
update `abstract` a
set a.`index_dirty` = now()
where a.`pubmed_id` = new.`abstract`
and new.`gene` != 0;
