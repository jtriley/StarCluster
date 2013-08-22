# Copyright 2009-2013 Justin Riley
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

condor_tmpl = """\
CONDOR_HOST = %(CONDOR_HOST)s
LOCAL_DIR = /var/lib/condor
LOCAL_CONFIG_FILE =
RUN = $(LOCAL_DIR)
LOG     = $(LOCAL_DIR)/log
LOCK = $(LOG)
SPOOL       = $(LOCAL_DIR)/spool
EXECUTE     = $(LOCAL_DIR)/execute
CRED_STORE_DIR = $(LOCAL_DIR)/cred_dir
UID_DOMAIN      = $(CONDOR_HOST)
FILESYSTEM_DOMAIN   = $(CONDOR_HOST)
TRUST_UID_DOMAIN = True
DAEMON_LIST = %(DAEMON_LIST)s
ALLOW_ADMINISTRATOR = $(CONDOR_HOST), node*
ALLOW_OWNER = $(FULL_HOSTNAME), $(ALLOW_ADMINISTRATOR), $(CONDOR_HOST), node*
ALLOW_READ = $(FULL_HOSTNAME), $(CONDOR_HOST), node*
ALLOW_WRITE = $(FULL_HOSTNAME), $(CONDOR_HOST), node*
SCHEDD_HOST = $(CONDOR_HOST)
START = True
SUSPEND = FALSE
PREEMPT = FALSE
KILL = FALSE
DedicatedScheduler = "DedicatedScheduler@$(CONDOR_HOST)"
STARTD_ATTRS = $(STARTD_ATTRS), DedicatedScheduler
SEC_DEFAULT_AUTHENTICATION_METHODS = FS, KERBEROS, GSI, FS_REMOTE
FS_REMOTE_DIR = %(FS_REMOTE_DIR)s
"""
