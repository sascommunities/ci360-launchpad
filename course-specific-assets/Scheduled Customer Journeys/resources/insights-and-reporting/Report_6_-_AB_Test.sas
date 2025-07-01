/* 6 Which variant in an A/B Test is the most successful? */
%let variant_node_name_list="June Teaser Variant A", "June Teaser Variant B";
proc sql;
	create table ab_test_result as  
	select j.journey_nm
		, n.node_nm
		, count(*) as success_count
	from udm.JOURNEY_NODE_ENTRY e 
	inner join udm.JOURNEY_SUCCESS s on s.journey_occurrence_id = e.journey_occurrence_id and s.identity_id = e.identity_id
	inner join udm.MD_JOURNEY_NODE n on e.node_id = n.journey_node_id 
	inner join udm.md_journey j on j.journey_id=n.journey_id
	where n.node_nm in (&variant_node_name_list.)
	group by j.journey_nm, n.node_nm
	order by j.journey_nm, n.node_nm;
QUIT;		


