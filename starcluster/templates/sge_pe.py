#!/usr/bin/env python
sge_pe_template = """
pe_name           orte
slots             %s
user_lists        NONE
xuser_lists       NONE
start_proc_args   /bin/true
stop_proc_args    /bin/true
allocation_rule   $round_robin
control_slaves    TRUE
job_is_first_task FALSE
urgency_slots     min
accounting_summary FALSE
"""
