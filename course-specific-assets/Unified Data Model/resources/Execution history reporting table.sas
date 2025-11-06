/******************************************************************************/
/* Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved. */
/* SPDX-License-Identifier: Apache-2.0                                        */
/* ****************************************************************************/
/* Objective: Provide an overview of task and segment map execution.  */
/* ****************************************************************************/

/* Point to the UDM in a relational database. */
/*libname udm ...; */


/* 1. Keep only the last published version of each task */
PROC SORT data=UDM.MD_TASK 
	out=MD_TASK;
	by TASK_ID LAST_PUBLISHED_DTTM;
run;
data MD_TASK;
 set MD_TASK;
	by TASK_ID;
	if last.TASK_ID;
run;


/* 2. Keep only the last published version of each segment map */
PROC SORT data=UDM.MD_SEGMENT_MAP 
	out=MD_SEGMENT_MAP;
	by SEGMENT_MAP_ID LAST_PUBLISHED_DTTM;
run;
data MD_SEGMENT_MAP;
 set MD_SEGMENT_MAP;
	by SEGMENT_MAP_ID;
	if last.SEGMENT_MAP_ID;
run;

/* 3. Get execution occurrences for tasks and segment maps */
PROC SQL;
	CREATE TABLE WORK.MD_OCCURRENCE AS 
	SELECT t1.OBJECT_TYPE_NM,
		t2.TASK_NM as OBJECT_NM,
		t1.EXECUTION_STATUS_CD as status, 
		t1.OCCURRENCE_NO, 
		t1.START_TM format=datetime27., 
		t1.END_TM format=datetime27.,
		t2.CHANNEL_NM as Channel
	FROM UDM.MD_OCCURRENCE t1, UDM.MD_TASK t2
	WHERE t1.OBJECT_ID = t2.TASK_ID
	UNION
	SELECT t1.OBJECT_TYPE_NM ,
		t3.SEGMENT_MAP_NM as OBJECT_NM,
		t1.EXECUTION_STATUS_CD as status, 
		t1.OCCURRENCE_NO, 
		t1.START_TM format=datetime27., 
		t1.END_TM format=datetime27.,
		t3.segment_map_category_nm as Channel
	FROM UDM.MD_OCCURRENCE t1, UDM.MD_SEGMENT_MAP t3
	WHERE t1.OBJECT_ID = t3.SEGMENT_MAP_ID
	order by START_TM desc;
QUIT;

/* 4. Add date levels */
data EXECUTION_HISTORY;
 length year week day 8;
 set MD_OCCURRENCE;
	year=year(datepart(START_TM));
	week=week(datepart(START_TM));
	day=datepart(START_TM);
 	duration=end_tm-start_TM;
	format day ddmmyy10.;
	format duration 8.2;
run;

/* clean up */
Proc delete data=
	MD_OCCURRENCE
	MD_SEGMENT_MAP
	MD_TASK
	;
run;


