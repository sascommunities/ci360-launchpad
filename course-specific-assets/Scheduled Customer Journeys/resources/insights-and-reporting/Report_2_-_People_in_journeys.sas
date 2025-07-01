/* 2 How many people are in journeys? */
proc sql;
	create table journey_occurrence as  
	select o.journey_occurrence_id
	from udm.md_journey_occurrence o
	where start_dttm > datetime()-60*24*60*60; /*lookback 60 days*/
quit;

proc sql;
	create table in_journey as
	select n.journey_occurrence_id
   		, n.identity_id
		, case when x.identity_id="" then 1 else 0 end as customer_count
	from UDM.journey_entry n
	left join UDM.journey_exit x 
		on  n.journey_occurrence_id = x.journey_occurrence_id
			and n.identity_id = x.identity_id
	where n.journey_occurrence_id in 
		(select journey_occurrence_id from journey_occurrence);
quit;

proc sql;
 	create table people_in_journey as
	select identity_id
		, sum(customer_count) as journey_nbr
	from in_journey
	where customer_count=1
	group by identity_id;
quit;

title Customers in journeys;
proc sql;
	select journey_nbr label="Number of journeys"
		,count(identity_id) label="Number of customers"
	from people_in_journey
	group by journey_nbr;
quit;
title;