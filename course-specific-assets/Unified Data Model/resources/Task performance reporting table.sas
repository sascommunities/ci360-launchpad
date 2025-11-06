/******************************************************************************/
/* Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved. */
/* SPDX-License-Identifier: Apache-2.0                                        */
/* ****************************************************************************/
/* Calculate the contacts, milestones and conversions per task.  */
/* Create a task performance reporting table with one row per triggered task and bulk task run. */
/* ****************************************************************************/

/* Define a UDM libname.*/

/* Set the lookback to process only the history that makes business sense. */
%let lookback = '01JAN2025:00:00:00'dt;

/* 1 extract contact history data */
proc sql; 
	create table CONTACT_HISTORY_subset as 
	select ch.CONTACT_ID
		, ch.IDENTITY_ID
		, ch.CONTACT_DTTM_TZ
		, ch.TASK_ID
		, ch.OCCURRENCE_ID
		, ch.RESPONSE_TRACKING_CD		
/*		, ch.CONTACT_NM*/ /* Not required here, but helps understand the nature of contacts */
	from UDM.CONTACT_HISTORY ch
	where ch.CONTACT_DTTM_TZ > &lookback.
;
quit; 

/* 2 extract conversion and milestone data */
/* A Conversion event occur when a contact reaches a primary metrics for a task. */
/* A Milestone event occur when a contact reaches a secondary metrics for a task. */
proc sql; 
	create table CONVERSION_MILESTONE_subset as 
	select cm.EVENT_ID
		, cm.IDENTITY_ID
		, cm.CONVERSION_MILESTONE_DTTM_TZ
/*		, cm.TASK_ID*/ 			/* Not required. RESPONSE_TRACKING_CD will be in the join key */
/*		, cm.OCCURRENCE_ID*/ 	/* Not required. RESPONSE_TRACKING_CD will be in the join key */
		, cm.RESPONSE_TRACKING_CD		
		, case when cm.event_nm='milestone'  then 1 else 0 end as milestone_cnt
		, case when cm.event_nm='conversion' then 1 else 0 end as conversion_cnt
	from UDM.CONVERSION_MILESTONE cm
	where cm.conversion_milestone_dttm_tz > &lookback.
;
quit; 

/* 3 combine the above */
proc sql; 
	create table INTERACTIONS_subset as 
	select ch.CONTACT_ID
		, ch.IDENTITY_ID
		, ch.CONTACT_DTTM_TZ
		, ch.TASK_ID
		, ch.OCCURRENCE_ID
		, ch.RESPONSE_TRACKING_CD
/*		, cm.EVENT_ID*/
/*		, cm.CONVERSION_MILESTONE_DTTM_TZ*/
		, coalesce(cm.milestone_cnt,0)  as milestone_cnt
		, coalesce(cm.conversion_cnt,0) as conversion_cnt
	from CONTACT_HISTORY_subset ch
	LEFT JOIN CONVERSION_MILESTONE_subset cm
		on ch.IDENTITY_ID=cm.IDENTITY_ID and ch.RESPONSE_TRACKING_CD=cm.RESPONSE_TRACKING_CD
;
quit; 

/* 4 Aggregate by identity */
/* When the same identity converts twice conversions=2 and unique_conversions=1 */
proc sql;
	create table interaction_by_identity as
	select TASK_ID
		, OCCURRENCE_ID
		, RESPONSE_TRACKING_CD
		, IDENTITY_ID
		, max(CONTACT_DTTM_TZ) as most_recent_contact_dttm format=datetime20.
		, count(distinct CONTACT_ID) as contacts
		, max(milestone_cnt)  as unique_milestones
		, max(conversion_cnt) as unique_conversions
		, sum(milestone_cnt)  as milstones
		, sum(conversion_cnt) as conversions
	from INTERACTIONS_subset
	group by TASK_ID, OCCURRENCE_ID, RESPONSE_TRACKING_CD, IDENTITY_ID
;
quit; 

/* 5 Aggregated by task run and task activation. */
proc sql;
	create table interaction_by_run as
	select TASK_ID
		, OCCURRENCE_ID
		, RESPONSE_TRACKING_CD
		, max(most_recent_contact_dttm) as most_recent_contact_dttm format=datetime20.
		, sum(contacts) as contacts
		, sum(unique_milestones)  as unique_milestones
		, sum(unique_conversions) as unique_conversions
		, sum(conversions) as conversions
		, sum(milstones)  as milstones
	from interaction_by_identity
	group by TASK_ID, OCCURRENCE_ID, RESPONSE_TRACKING_CD
;
quit; 

/* 6 Add task and occurrence metadata */
proc sql; 
	create table task_performance as 
	select i.most_recent_contact_dttm
		, t.CHANNEL_NM
		, t.TASK_DELIVERY_TYPE_NM
		, t.TASK_SUBTYPE_NM
		, t.TASK_NM
		, t.TASK_CD
		, o.OCCURRENCE_NO
		, o.END_TM as occurrence_run_dttm format=datetime20.
		, i.contacts
		, i.unique_milestones
		, i.unique_conversions
		, i.conversions
		, i.milstones
		, t.TASK_TYPE_NM, t.TASK_STATUS_CD, t.TASK_DESC, t.OWNER_NM, t.TASK_ID
		, i.RESPONSE_TRACKING_CD, i.OCCURRENCE_ID
	from 		UDM.MD_TASK t 
	inner join	interaction_by_run i on i.task_id=t.task_id
	left join	UDM.MD_occurrence o on i.OCCURRENCE_ID=o.OCCURRENCE_ID
	order by most_recent_contact_dttm desc
;
quit; 

/* 7 Delete temporary  tables */
/*
proc delete data=
	work.contact_history_subset
	work.conversion_milestone_subset
	work.interactions_subset
	work.interaction_by_identity
	work.interaction_by_run
	;
run;
*/