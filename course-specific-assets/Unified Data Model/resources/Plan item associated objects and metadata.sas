/******************************************************************************/
/* Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved. */
/* SPDX-License-Identifier: Apache-2.0                                        */
/* ****************************************************************************/

/*------------------------------------------------------------------------------------------------------*/
/*	Queries on plan tables  /
/*	Objective: */
/*		- Show how tasks and activities are associated to plan items */
/*		- Show how to group task and activities in a Plan hierarchy. */
/*		- Show how to join plan custom properties with plan items to enrich reports with plan metadata. */
/*------------------------------------------------------------------------------------------------------*/

/* udm LIBNAME*/
*libname udm XXXXX; 

   proc sql; 
	create table TASKS_BY_PLAN as 
	select       
		  pi.lev1_nm as Plan_NM
		, pi.lev2_nm as Campaign_NM
		, tsk.task_nm
		, tsk.task_cd 
		, tsk.task_desc length 60 format $60.
		, tsk.owner_nm
		, tsk.channel_nm         
		, tsk.task_status_cd         
		, tsk.task_id
		, pi.planning_id
	from udm.MD_TASK tsk
	left join udm.PLANNING_INFO pi on tsk.task_id=pi.task_id;
quit; 

proc sql; 
	create table TASKS_in_ACTIVITIES_BY_PLAN as 
	select
		  pia.lev1_nm as Plan_NM
		, pia.lev2_nm as Campaign_NM
		, tsk.task_nm
		, tsk.task_cd 
		, tsk.task_desc length 60 format $60.
		, tsk.owner_nm
		, tsk.channel_nm         
		, tsk.task_status_cd         
		, tsk.task_id
		, a.activity_id
		, pia.planning_id
	from udm.MD_TASK tsk
	inner join udm.MD_Activity_X_Task at on at.task_id=tsk.task_id
	inner join udm.MD_Activity a on at.activity_id=a.activity_id
	left join udm.PLANNING_INFO pia on at.activity_id=pia.activity_id
	;
quit; 

/* Get Task details from planning_info tables with a specific custom property value from a grid */
PROC SQL;
  CREATE TABLE WORK.plan_metadata AS
  SELECT
     t1.lev1_nm, t1.lev2_nm, t1.lev3_nm, t1.lev4_nm,
     t1.task_channel, t1.task_status,
     t1.task_nm, t1.task_id,  t2.attr_nm, t2.attr_val, 
     t1.planning_nm,
     t1.planning_type, t1.planning_level_type, 
     t1.parent_nm,
	 t1.planning_id
  FROM
     udm.planning_info t1,
     udm.planning_info_custom_prop t2
  where t1.planning_id = t2.planning_id
  ;
QUIT;