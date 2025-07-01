/* 1 How successful is each journey? */
/* Combination of two steps in one query */
proc sql;
	create table success_overview as  
	select p.purpose_nm 
		, j.journey_nm 
		, o.journey_occurrence_num 
		, o.num_of_contacts_entered
		, o.num_of_contacts_suppressed
		, s.success_val 
		, s.unit_qty
		, coalesce(s.success_nbr,0) as success_nbr  
	from udm.md_journey j  
	left join udm.md_purpose p on j.purpose_id=p.purpose_id 
	inner join udm.md_journey_occurrence o on j.journey_id=o.journey_id 
	left join (
			select journey_occurrence_id 
				, sum(unit_qty) as unit_qty 
				, sum(success_val) as success_val 
				, count(event_id) as success_nbr 
			from udm.journey_success 
			where success_dttm > datetime() - 1*365*24*60*60 
			group by journey_occurrence_id
		)  s on o.journey_occurrence_id=s.journey_occurrence_id 
	order by p.purpose_nm, j.journey_nm, o.journey_occurrence_num;
quit;