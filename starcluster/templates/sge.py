#!/usr/bin/env python

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
ADMIN_HOST_LIST="%s"
SUBMIT_HOST_LIST="%s"
EXEC_HOST_LIST="%s"
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
"""
