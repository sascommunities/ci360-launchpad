/* 3 Which audiences are used in journeys? */

/*Simplified version commented out */
/*
proc sql;
	create table audiences_in_journeys as  
	select j.journey_nm
		, jo.journey_occurrence_num
		, jo.start_dttm as journey_execution_dttm format=datetime.
		, a.audience_nm
		, ao.start_tm as audience_execution_dttm format=datetime.
		, datepart(jo.start_dttm) - datepart(ao.start_tm) as days_between_upload_and_use
		, datepart(ao.start_tm)+a.audience_expiration_val-datepart(jo.start_dttm) as days_until_audience_expiration
	from udm.md_journey j
	inner join udm.md_journey_occurrence jo on j.journey_id=jo.journey_id
	inner join udm.md_audience_occurrence ao on ao.aud_occurrence_id=jo.aud_occurrence_id
	inner join udm.md_audience a on a.audience_id=ao.audience_id
	where audience_execution_dttm > datetime() - 1*365*24*60*60;
quit;
*/

proc sql;
	create table audiences_in_journeys as  
	select j.journey_nm
		, jo.journey_occurrence_num
		, jo.start_dttm as journey_execution_dttm format=datetime.
		, a.audience_nm
		, ao.start_tm as audience_execution_dttm format=datetime.
		, datepart(jo.start_dttm) - datepart(ao.start_tm) as days_between_upload_and_use
		, datepart(ao.start_tm)+a.audience_expiration_val-datepart(jo.start_dttm) as days_until_audience_expiration
	from udm.md_journey j
	inner join udm.md_journey_occurrence jo on j.journey_id=jo.journey_id
	inner join (select journey_id , max(journey_occurrence_num) as journey_occurrence_num 
				from udm.md_journey_occurrence 
				group by journey_id
			) jon on jo.journey_id=jon.journey_id and jo.journey_occurrence_num=jon.journey_occurrence_num
	inner join udm.md_audience_occurrence ao on ao.aud_occurrence_id=jo.aud_occurrence_id
	inner join udm.md_audience a on a.audience_id=ao.audience_id
	where audience_execution_dttm > datetime() - 1*365*24*60*60	;
quit;

