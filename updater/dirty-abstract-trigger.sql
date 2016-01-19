create trigger `mark_dirty_gene_abstracts`
after insert on `gene_abstract`
for each row
update `abstract` a
set a.`index_dirty` = now()
where a.`pubmed_id` = new.`abstract`
and new.`gene` != 0;



create trigger `mark_dirty_metabolite_abstracts`
after insert on `metabolite_abstract`
for each row
update `abstract` a
set a.`index_dirty` = now()
where a.`pubmed_id` = new.`abstract`
and new.`metabolite_hmdb_id` != 0;
