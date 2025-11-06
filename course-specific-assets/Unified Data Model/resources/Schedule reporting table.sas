/******************************************************************************/
/* Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved. */
/* SPDX-License-Identifier: Apache-2.0                                        */
/* ****************************************************************************/
/* Objective: Provide an overview of planned task and segment map executions. */
/* ****************************************************************************/

/* Point to the UDM in a relational database. */
/*libname udm ...; */

PROC SQL;
	CREATE TABLE TASK_SCHEDULE AS 
	SELECT
		'task' as object_type length=15, 
		t1.task_nm as object_nm, 
		t1.scheduled_start_dttm, 
		t1.scheduled_end_dttm, 

		t1.rec_scheduled_start_tm, 
		t1.recurrence_frequency_cd, 
		t1.recurrence_days_of_week_txt, 
		t1.recurrence_monthly_type_nm, 
		t1.recurrence_day_of_month_no, 
		t1.recurrence_day_of_week_txt, 
		t1.recurrence_day_of_wk_ordinal_no, 
		t1.recurring_schedule_flg, 

		t1.channel_nm as category, 
		t1.task_status_cd as object_status_cd, 
		t1.task_cd as object_cd, 
		t1.task_id as object_id, 
		t1.owner_nm
	FROM UDM.MD_TASK t1
	WHERE t1.scheduled_flg="1" and (scheduled_end_dttm > datetime() or scheduled_end_dttm =.)
;
QUIT;


PROC SQL;
	CREATE TABLE SEGMENT_MAP_SCHEDULE AS 
	SELECT 
		'segment map' as object_type, 
		t1.segment_map_nm as object_nm,
		t1.scheduled_start_dttm, 
		t1.scheduled_end_dttm, 

		t1.rec_scheduled_start_tm, 
		t1.recurrence_frequency_cd, 
		t1.recurrence_days_of_week_txt, 
		t1.recurrence_monthly_type_nm, 
		t1.recurrence_day_of_month_no, 
		t1.recurrence_day_of_week_txt, 
		t1.recurrence_day_of_wk_ordinal_no,

		t1.segment_map_category_nm as category, 
		t1.segment_map_status_cd as object_status_cd, 
		t1.segment_map_cd as object_cd, 
		t1.segment_map_id as object_id, 
		t1.owner_nm
	FROM UDM.MD_SEGMENT_MAP t1
	WHERE t1.scheduled_flg="1" and (scheduled_end_dttm > datetime() or scheduled_end_dttm =.);
	;
QUIT;


%macro next_weekly_run(sched_weekday_num=);
	do;
		next_run=min(next_run, next_opportunity_to_run + mod(&sched_weekday_num. - weekday(next_opportunity_to_run), 7));
		if next_run < next_opportunity_to_run or (input(rec_scheduled_start_tm,time.) < time() and next_run=today() ) 
			then next_run=next_run+7;
	end;
%mend;

data SCHEDULE_OVERVIEW (drop=next_opportunity_to_run temp_month_run last_day first_day weekday_offset rec_day_of_week_no wk_offset);
 	next_run='31dec2999'd;
	start_time=.;
	set TASK_SCHEDULE SEGMENT_MAP_SCHEDULE;

 	next_opportunity_to_run=max(datepart(scheduled_start_dttm),today());	

	if recurrence_frequency_cd="daily" then do;
		if next_opportunity_to_run = today() and input(rec_scheduled_start_tm,time.) < time() 
			then next_run= today()+1;
			else next_run=next_opportunity_to_run;
	end;
	else if recurrence_frequency_cd="weekly" then do;
		if index(recurrence_days_of_week_txt,'Sunday')   then %next_weekly_run(sched_weekday_num=1); 
		if index(recurrence_days_of_week_txt,'Monday')   then %next_weekly_run(sched_weekday_num=2);
		if index(recurrence_days_of_week_txt,'Tuesday')  then %next_weekly_run(sched_weekday_num=3);
		if index(recurrence_days_of_week_txt,'Wednesday')then %next_weekly_run(sched_weekday_num=4);
		if index(recurrence_days_of_week_txt,'Thursday') then %next_weekly_run(sched_weekday_num=5);
		if index(recurrence_days_of_week_txt,'Friday')   then %next_weekly_run(sched_weekday_num=6);
		if index(recurrence_days_of_week_txt,'Saturday') then %next_weekly_run(sched_weekday_num=7);
	end;
	else if recurrence_frequency_cd="monthly" and recurrence_monthly_type_nm='dayOfMonth' then do;
		if recurrence_day_of_month_no >	day(intnx('month',next_opportunity_to_run,0,'end')) 
			then next_opportunity_to_run=intnx('month',next_opportunity_to_run,1,'SAME');
		temp_month_run=mdy(month(next_opportunity_to_run), recurrence_day_of_month_no, year(next_opportunity_to_run));
		if next_opportunity_to_run > temp_month_run or 
		 (next_opportunity_to_run = today() and input(rec_scheduled_start_tm,time.) < time() )
			then next_run=intnx('month',temp_month_run,1,'SAME');
			else next_run=temp_month_run;
	end;
	else if recurrence_frequency_cd="monthly" and recurrence_monthly_type_nm='dayOfWeek' then do;
		     if recurrence_day_of_week_txt='sunday'    then rec_day_of_week_no=1;
		else if recurrence_day_of_week_txt='monday'    then rec_day_of_week_no=2;
		else if recurrence_day_of_week_txt='tuesday'   then rec_day_of_week_no=3;
		else if recurrence_day_of_week_txt='wednesday' then rec_day_of_week_no=4;
		else if recurrence_day_of_week_txt='thursday'  then rec_day_of_week_no=5;
		else if recurrence_day_of_week_txt='friday'    then rec_day_of_week_no=6;
		else if recurrence_day_of_week_txt='saturday'  then rec_day_of_week_no=7;

		if      recurrence_day_of_wk_ordinal_no='first'  then wk_offset=0; 
		else if recurrence_day_of_wk_ordinal_no='second' then wk_offset=1; 
		else if recurrence_day_of_wk_ordinal_no='third'  then wk_offset=2; 
		else if recurrence_day_of_wk_ordinal_no='fourth' then wk_offset=3; 

		if recurrence_day_of_wk_ordinal_no='last' then do;
			last_day =intnx('month',next_opportunity_to_run,0,'END');
			weekday_offset = mod(rec_day_of_week_no-weekday(last_day),7);
			if weekday_offset >0 then weekday_offset=weekday_offset-7;
			next_run = last_day + weekday_offset;
			if next_opportunity_to_run > next_run or
		 		(next_opportunity_to_run = today() and input(rec_scheduled_start_tm,time.) < time() )
				then do;
					last_day =intnx('month',next_opportunity_to_run,1,'END');
					weekday_offset = mod(rec_day_of_week_no-weekday(last_day),7);
					if weekday_offset >0 then weekday_offset=weekday_offset-7;
					next_run = last_day + weekday_offset;
				end;
		end;
		else do;
			first_day = mdy(month(next_opportunity_to_run), 1, year(next_opportunity_to_run));
			weekday_offset = mod(rec_day_of_week_no - weekday(first_day) + 7, 7);
		    next_run = first_day + weekday_offset + 7*wk_offset;
			if next_opportunity_to_run > next_run or
		 		(next_opportunity_to_run = today() and input(rec_scheduled_start_tm,time.) < time() )
				then do;
					first_day = intnx('month',next_opportunity_to_run,1,'BEGINNING');
					weekday_offset = mod(rec_day_of_week_no - weekday(first_day) + 7, 7);
				    next_run = first_day + weekday_offset + 7 *wk_offset;
				end;
		end;
	end;
	else if recurrence_frequency_cd="" or recurring_schedule_flg="0" then do; /* one shot */
		next_run=datepart(scheduled_start_dttm);
	end;

    start_time=input(rec_scheduled_start_tm,time.) ;	
	if start_time=. then start_time=timepart(scheduled_start_dttm);
	format start_time time.;
	format next_run weekdatx37.;
run;

proc sort;
	by next_run start_time;
run;


proc delete data=
	TASK_SCHEDULE
	SEGMENT_MAP_SCHEDULE;
run;


