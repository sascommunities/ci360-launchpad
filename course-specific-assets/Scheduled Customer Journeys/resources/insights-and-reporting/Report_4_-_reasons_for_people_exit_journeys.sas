/* 4 What are the most common reasons for people exit journeys? */
proc sql;
	create table journey_occ_id_drop_reason as  
	select journey_occurrence_id
        , reason_cd
        , reason_txt
		, count(identity_id) as member_nbr
	from udm.journey_exit
	where exit_dttm > datetime() - 1*365*24*60*60
	group by journey_occurrence_id
        , reason_txt
        , reason_cd;
quit;

proc sql;
	create table journey_drop_reason as  
	select j.journey_nm
		, o.journey_occurrence_num
		, d.reason_cd
		, d.reason_txt
		, d.member_nbr
	from journey_occ_id_drop_reason d
	inner join udm.md_journey_occurrence o on d.journey_occurrence_id = o.journey_occurrence_id 
	inner join udm.md_journey j on  j.journey_id=o.journey_id
	order by j.journey_nm
		, o.journey_occurrence_num;
quit;

