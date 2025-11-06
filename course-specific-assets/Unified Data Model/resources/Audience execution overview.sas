/******************************************************************************/
/* Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved. */
/* SPDX-License-Identifier: Apache-2.0                                        */
/* ****************************************************************************/
/* Objective: provide insights to the success and the size of audience executions.  */
/* ****************************************************************************/

/* Point to the UDM in a relational database. */
/*libname udm ...; */

/* 1. Count successfull and unsuccesfull audience runs */
proc sql;
	create table AUDIENCE_EXECUTION_STATUS as
	select audience_id,  
		sum(case when execution_status_cd='ACTIVE' then 1 else 0 end) AS succesfull_runs,
		sum(case when execution_status_cd='ACTIVE' then 0 else 1 end) AS other_runs
	from UDM.MD_AUDIENCE_OCCURRENCE
	group by audience_id;
quit;


/* 2. Get details of the most recent audience run */
PROC SORT data=UDM.MD_AUDIENCE_OCCURRENCE
	out=AUDIENCE_LAST_RUN(drop=started_by_nm);
	by audience_id start_tm;
RUN;
data AUDIENCE_LAST_RUN;
 set AUDIENCE_LAST_RUN;
	by audience_id;
	if last.audience_id then output;
run;


/* 3. Combine with audience metadata */
PROC SQL;
	CREATE TABLE AUDIENCE_USAGE AS 
	SELECT 
		lr.start_tm FORMAT=DATETIME27. AS last_run, 
		au.audience_nm, 
		au.audience_data_source_nm,
		lr.execution_status_cd, 
		lr.audience_size_val as last_audience_size, 
		(lr.end_tm-lr.start_tm)/60  format=5. as last_run_in_minutes, 
		es.succesfull_runs,
		es.other_runs,
		au.audience_id,
		au.audience_source_nm
	FROM UDM.MD_AUDIENCE au
	INNER JOIN AUDIENCE_EXECUTION_STATUS es 
		ON (au.audience_id = es.audience_id)
	INNER JOIN AUDIENCE_LAST_RUN lr 
		ON (au.audience_id = lr.audience_id )
	order by last_run desc
	;
QUIT;
