/* 5 How many selected customers were suppressed and why? */
proc sql;
	create table journey_occ_id_suppress_reason as  
	select s.journey_occurrence_id
		, s.aud_occurrence_id
		, s.reason_cd
		, s.reason_txt
		, count(distinct s.identity_id) as members_suppressed
	from  udm.journey_suppression s 
	where suppression_dttm > datetime() - 1*365*24*60*60
	group by s.journey_occurrence_id
		, s.aud_occurrence_id
		, s.reason_cd
		, s.reason_txt;
quit;

proc sql;
	create table journey_suppression_reason as  
	select j.journey_nm
		, jo.journey_occurrence_num
		, a.audience_nm
		, ao.audience_size_val
		, d.reason_cd
		, d.reason_txt
		, d.members_suppressed
	from udm.md_journey j
	inner join udm.md_journey_occurrence jo on j.journey_id=jo.journey_id
	inner join journey_occ_id_suppress_reason d on d.journey_occurrence_id = jo.journey_occurrence_id 
	inner join udm.md_audience_occurrence ao on ao.aud_occurrence_id=jo.aud_occurrence_id
	inner join udm.md_audience a on a.audience_id=ao.audience_id;
quit;

