# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

sgeinstall_template = """
SGE_CLUSTER_NAME="starcluster"
SGE_ROOT="/opt/sge6"
SGE_QMASTER_PORT="63231"
SGE_EXECD_PORT="63232"
SGE_ENABLE_SMF="false"
CELL_NAME="default"
ADMIN_USER=""
QMASTER_SPOOL_DIR="/opt/sge6/default/spool/qmaster"
EXECD_SPOOL_DIR="/opt/sge6/default/spool"
GID_RANGE="20000-20100"
SPOOLING_METHOD="classic"
DB_SPOOLING_SERVER="none"
DB_SPOOLING_DIR="/opt/sge6/default/spooldb"
PAR_EXECD_INST_COUNT="20"
ADMIN_HOST_LIST="%(admin_hosts)s"
SUBMIT_HOST_LIST="%(submit_hosts)s"
EXEC_HOST_LIST="%(exec_hosts)s"
EXECD_SPOOL_DIR_LOCAL="/opt/sge6/default/spool/exec_spool_local"
HOSTNAME_RESOLVING="true"
SHELL_NAME="ssh"
COPY_COMMAND="scp"
DEFAULT_DOMAIN="none"
ADMIN_MAIL="none@none.edu"
ADD_TO_RC="false"
SET_FILE_PERMS="true"
RESCHEDULE_JOBS="wait"
SCHEDD_CONF="1"
SHADOW_HOST=""
EXEC_HOST_LIST_RM=""
REMOVE_RC="true"
WINDOWS_SUPPORT="false"
WIN_ADMIN_NAME="Administrator"
WIN_DOMAIN_ACCESS="false"
CSP_RECREATE="false"
CSP_COPY_CERTS="false"
CSP_COUNTRY_CODE="US"
CSP_STATE="MA"
CSP_LOCATION="BOSTON"
CSP_ORGA="MIT"
CSP_ORGA_UNIT="OEIT"
CSP_MAIL_ADDRESS="none@none.edu"
"""

sge_pe_template = """
pe_name           %s
slots             %s
user_lists        NONE
xuser_lists       NONE
start_proc_args   /bin/true
stop_proc_args    /bin/true
allocation_rule   $fill_up
control_slaves    TRUE
job_is_first_task FALSE
urgency_slots     min
accounting_summary FALSE
"""

sgeprofile_template = """
export SGE_ROOT="/opt/sge6"
export SGE_CELL="default"
export SGE_CLUSTER_NAME="starcluster"
export SGE_QMASTER_PORT="63231"
export SGE_EXECD_PORT="63232"
export MANTYPE="man"
export MANPATH="$MANPATH:$SGE_ROOT/man"
export PATH="$PATH:$SGE_ROOT/bin/%(arch)s"
export ROOTPATH="$ROOTPATH:$SGE_ROOT/bin/%(arch)s"
export LDPATH="$LDPATH:$SGE_ROOT/lib/%(arch)s"
export DRMAA_LIBRARY_PATH="$SGE_ROOT/lib/%(arch)s/libdrmaa.so"
"""

host_group_template= """
group_name %(group_name)s

hostlist %(host_list)s
"""

queue_template= """
qname                 %(queue_name)s
hostlist              %(host_group)s
seq_no                %(seq_no)d
load_thresholds       np_load_avg=1.75
suspend_thresholds    NONE
nsuspend              1
suspend_interval      00:05:00
priority              0
min_cpu_interval      00:05:00
processors            UNDEFINED
qtype                 BATCH INTERACTIVE
ckpt_list             NONE
pe_list               make orte
rerun                 FALSE
slots                 %(slots)d
tmpdir                /tmp
shell                 /bin/bash
prolog                NONE
epilog                NONE
shell_start_mode      posix_compliant
starter_method        NONE
suspend_method        NONE
resume_method         NONE
terminate_method      NONE
notify                00:00:60
owner_list            NONE
user_lists            NONE
xuser_lists           NONE
subordinate_list      NONE
complex_values        NONE
projects              NONE
xprojects             NONE
calendar              NONE
initial_state         default
s_rt                  INFINITY
h_rt                  INFINITY
s_cpu                 INFINITY
h_cpu                 INFINITY
s_fsize               INFINITY
h_fsize               INFINITY
s_data                INFINITY
h_data                INFINITY
s_stack               INFINITY
h_stack               INFINITY
s_core                INFINITY
h_core                INFINITY
s_rss                 INFINITY
h_rss                 INFINITY
s_vmem                INFINITY
h_vmem                INFINITY
"""
