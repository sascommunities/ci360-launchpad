/******************************************************************************/
/* Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved. */
/* SPDX-License-Identifier: Apache-2.0                                        */
/* ****************************************************************************/

%macro check_recent_load (lib_name=,table_name=, column_name=, data_after=);
	%local lib_name table_name column_name data_after row_counter;
	%let row_counter=0;
	proc sql noprint;
		select count(*) into :row_counter
		from &lib_name..&table_name. 
		where &column_name. > &data_after.;
	quit;
	%if &row_counter.=0 %then %do;
		%let SYSCC=5; /* set the condition code that SAS returns to your operating system. 4 is a warning. Greater is an error. */      
		%put ERR%str()OR: &lib_name..&table_name. contains no recent data. Check the load process.;
		%put ERR%str()OR- The applied filter is &column_name. > &data_after.;
		%put ERR%str()OR- Formated as a date is &column_name. > %sysfunc(putn(&data_after.,date9.));
		%put ERR%str()OR- and for a datetime is &column_name. > %sysfunc(putn(&data_after.,datetime.));
	%end;
	%else %do;
		%put NOTE: &SYSMACRONAME found recent data.;
	%end;
%mend;


/* example */
/*
%check_recent_load(
	lib_name   =UDM,
	table_name =CONTACT_HISTORY, 
	column_name=CONTACT_DTTM, 
	data_after =%sysfunc(datetime()) - 2*24*3600 ); * now minus 2 days;
*/
