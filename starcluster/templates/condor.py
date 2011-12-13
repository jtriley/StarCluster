condor_tmpl = """\
CONDOR_HOST = master
RELEASE_DIR     = /usr
LOCAL_DIR       = /var/lib/condor
LOCAL_CONFIG_FILE   = /etc/condor_config.local
MAIL            = /usr/bin/mail
UID_DOMAIN      = master
FILESYSTEM_DOMAIN   = master
COLLECTOR_NAME      = Ubuntu Default Personal Pool
FLOCK_FROM = master
FLOCK_TO = node*
FLOCK_NEGOTIATOR_HOSTS = $(FLOCK_TO)
FLOCK_COLLECTOR_HOSTS = $(FLOCK_TO)
HOSTALLOW_ADMINISTRATOR = $(CONDOR_HOST) node*
HOSTALLOW_OWNER = $(FULL_HOSTNAME), $(HOSTALLOW_ADMINISTRATOR) node*
HOSTALLOW_READ = $(FULL_HOSTNAME) node*
HOSTALLOW_WRITE = $(FULL_HOSTNAME) node*
HOSTALLOW_NEGOTIATOR = $(CONDOR_HOST)
HOSTALLOW_NEGOTIATOR_SCHEDD = $(CONDOR_HOST), $(FLOCK_NEGOTIATOR_HOSTS)
HOSTALLOW_WRITE_COLLECTOR = $(HOSTALLOW_WRITE), $(FLOCK_FROM)
HOSTALLOW_WRITE_STARTD    = $(HOSTALLOW_WRITE), $(FLOCK_FROM)
HOSTALLOW_READ_COLLECTOR  = $(HOSTALLOW_READ), $(FLOCK_FROM)
HOSTALLOW_READ_STARTD     = $(HOSTALLOW_READ), $(FLOCK_FROM)
LOCK        = $(LOG)
GLIDEIN_SERVER_URLS = \
  http://www.cs.wisc.edu/condor/glidein/binaries
ALL_DEBUG               =
MAX_COLLECTOR_LOG   = 1000000
COLLECTOR_DEBUG     =
MAX_KBDD_LOG        = 1000000
KBDD_DEBUG      =
MAX_NEGOTIATOR_LOG  = 1000000
NEGOTIATOR_DEBUG    = D_MATCH
MAX_NEGOTIATOR_MATCH_LOG = 1000000
MAX_SCHEDD_LOG      = 1000000
SCHEDD_DEBUG        = D_PID
MAX_SHADOW_LOG      = 1000000
SHADOW_DEBUG        =
MAX_STARTD_LOG      = 1000000
STARTD_DEBUG        =
MAX_STARTER_LOG     = 1000000
STARTER_DEBUG       = D_NODATE
MAX_MASTER_LOG      = 1000000
MASTER_DEBUG        =
MAX_JOB_ROUTER_LOG      = 1000000
JOB_ROUTER_DEBUG        =
MAX_HAD_LOG     = 1000000
HAD_DEBUG       =
MAX_REPLICATION_LOG = 1000000
REPLICATION_DEBUG   =
MAX_TRANSFERER_LOG  = 1000000
TRANSFERER_DEBUG    =
MINUTE      = 60
HOUR        = (60 * $(MINUTE))
StateTimer  = (CurrentTime - EnteredCurrentState)
ActivityTimer   = (CurrentTime - EnteredCurrentActivity)
ActivationTimer = (CurrentTime - JobStart)
LastCkpt    = (CurrentTime - LastPeriodicCheckpoint)
STANDARD    = 1
VANILLA     = 5
MPI     = 8
VM      = 13
IsMPI           = (TARGET.JobUniverse == $(MPI))
IsVanilla       = (TARGET.JobUniverse == $(VANILLA))
IsStandard      = (TARGET.JobUniverse == $(STANDARD))
IsVM            = (TARGET.JobUniverse == $(VM))
NonCondorLoadAvg    = (LoadAvg - CondorLoadAvg)
BackgroundLoad      = 0.3
HighLoad        = 0.5
StartIdleTime       = 15 * $(MINUTE)
ContinueIdleTime    =  5 * $(MINUTE)
MaxSuspendTime      = 10 * $(MINUTE)
MaxVacateTime       = 10 * $(MINUTE)
KeyboardBusy        = (KeyboardIdle < $(MINUTE))
ConsoleBusy     = (ConsoleIdle  < $(MINUTE))
CPUIdle         = ($(NonCondorLoadAvg) <= $(BackgroundLoad))
CPUBusy         = ($(NonCondorLoadAvg) >= $(HighLoad))
KeyboardNotBusy     = ($(KeyboardBusy) == False)
BigJob      = (TARGET.ImageSize >= (50 * 1024))
MediumJob = (TARGET.ImageSize >= (15 * 1024) && TARGET.ImageSize < (50 * 1024))
SmallJob    = (TARGET.ImageSize <  (15 * 1024))
JustCPU         = ($(CPUBusy) && ($(KeyboardBusy) == False))
MachineBusy     = ($(CPUBusy) || $(KeyboardBusy))
WANT_SUSPEND        = $(TESTINGMODE_WANT_SUSPEND)
WANT_VACATE     = $(TESTINGMODE_WANT_VACATE)
START           = $(TESTINGMODE_START)
START_LOCAL_UNIVERSE    = True
START_SCHEDULER_UNIVERSE    = True
SUSPEND         = $(TESTINGMODE_SUSPEND)
CONTINUE        = $(TESTINGMODE_CONTINUE)
PREEMPT         = $(UWCS_PREEMPT)
KILL            = $(TESTINGMODE_KILL)
PERIODIC_CHECKPOINT = $(TESTINGMODE_PERIODIC_CHECKPOINT)
PREEMPTION_REQUIREMENTS = $(TESTINGMODE_PREEMPTION_REQUIREMENTS)
PREEMPTION_RANK     = $(TESTINGMODE_PREEMPTION_RANK)
NEGOTIATOR_PRE_JOB_RANK = $(UWCS_NEGOTIATOR_PRE_JOB_RANK)
NEGOTIATOR_POST_JOB_RANK = $(UWCS_NEGOTIATOR_POST_JOB_RANK)
MaxJobRetirementTime    = $(UWCS_MaxJobRetirementTime)
CLAIM_WORKLIFE          = $(UWCS_CLAIM_WORKLIFE)
UWCS_WANT_SUSPEND  = ( $(SmallJob) || $(KeyboardNotBusy) || $(IsVanilla) ) && \
                     ( $(SUSPEND) )
UWCS_WANT_VACATE   = ( $(ActivationTimer) > 10 * $(MINUTE) || $(IsVanilla) )
UWCS_START  = ( (KeyboardIdle > $(StartIdleTime)) \
                    && ( $(CPUIdle) || \
                         (State != "Unclaimed" && State != "Owner")) )
UWCS_SUSPEND = ( $(KeyboardBusy) || \
                 ( (CpuBusyTime > 2 * $(MINUTE)) \
                   && $(ActivationTimer) > 90 ) )
UWCS_CONTINUE = ( $(CPUIdle) && ($(ActivityTimer) > 10) \
                  && (KeyboardIdle > $(ContinueIdleTime)) )
UWCS_PREEMPT = ( ((Activity == "Suspended") && \
                  ($(ActivityTimer) > $(MaxSuspendTime))) \
         || (SUSPEND && (WANT_SUSPEND == False)) )
UWCS_MaxJobRetirementTime = 0
UWCS_KILL = $(ActivityTimer) > $(MaxVacateTime)
UWCS_PERIODIC_CHECKPOINT    = $(LastCkpt) > (3 * $(HOUR) + \
                                  $RANDOM_INTEGER(-30,30,1) * $(MINUTE) )
UWCS_NEGOTIATOR_PRE_JOB_RANK = RemoteOwner =?= UNDEFINED
UWCS_PREEMPTION_REQUIREMENTS = ( $(StateTimer) > (1 * $(HOUR)) && \
    RemoteUserPrio > SubmittorPrio * 1.2 ) || (MY.NiceUser == True)
UWCS_PREEMPTION_RANK = (RemoteUserPrio * 1000000) - TARGET.ImageSize
TESTINGMODE_WANT_SUSPEND    = False
TESTINGMODE_WANT_VACATE     = False
TESTINGMODE_START           = True
TESTINGMODE_SUSPEND         = False
TESTINGMODE_CONTINUE        = True
TESTINGMODE_PREEMPT         = False
TESTINGMODE_KILL            = False
TESTINGMODE_PERIODIC_CHECKPOINT = False
TESTINGMODE_PREEMPTION_REQUIREMENTS = False
TESTINGMODE_PREEMPTION_RANK = 0
TESTINGMODE_CLAIM_WORKLIFE = 1200
LOG     = $(LOCAL_DIR)/log
SPOOL       = $(LOCAL_DIR)/spool
EXECUTE     = $(LOCAL_DIR)/execute
ULIBDIR         = $(RELEASE_DIR)/lib/condor
BIN     = $(RELEASE_DIR)/bin
LIB     = $(ULIBDIR)/lib
SBIN        = $(RELEASE_DIR)/sbin
LIBEXEC     = $(ULIBDIR)/libexec
HISTORY     = $(SPOOL)/history
COLLECTOR_LOG   = $(LOG)/CollectorLog
KBDD_LOG    = $(LOG)/KbdLog
MASTER_LOG  = $(LOG)/MasterLog
NEGOTIATOR_LOG  = $(LOG)/NegotiatorLog
NEGOTIATOR_MATCH_LOG = $(LOG)/MatchLog
SCHEDD_LOG  = $(LOG)/SchedLog
SHADOW_LOG  = $(LOG)/ShadowLog
STARTD_LOG  = $(LOG)/StartLog
STARTER_LOG = $(LOG)/StarterLog
JOB_ROUTER_LOG  = $(LOG)/JobRouterLog
HAD_LOG     = $(LOG)/HADLog
REPLICATION_LOG = $(LOG)/ReplicationLog
TRANSFERER_LOG  = $(LOG)/TransfererLog
SHADOW_LOCK = $(LOCK)/ShadowLock
COLLECTOR_HOST  = $(CONDOR_HOST)
RESERVED_DISK       = 5
#DAEMON_LIST            = MASTER, STARTD, SCHEDD, COLLECTOR, NEGOTIATOR
DAEMON_LIST         = %(DAEMON_LIST)s
MASTER              = $(SBIN)/condor_master
STARTD              = $(SBIN)/condor_startd
SCHEDD              = $(SBIN)/condor_schedd
KBDD                = $(SBIN)/condor_kbdd
NEGOTIATOR          = $(SBIN)/condor_negotiator
COLLECTOR           = $(SBIN)/condor_collector
STARTER_LOCAL           = $(SBIN)/condor_starter
JOB_ROUTER                      = $(LIBEXEC)/condor_job_router
MASTER_ADDRESS_FILE = $(LOG)/.master_address
PREEN               = $(SBIN)/condor_preen
PREEN_ARGS          = -m -r
STARTER_LIST = STARTER, STARTER_STANDARD
STARTER         = $(SBIN)/condor_starter
STARTER_STANDARD    = $(SBIN)/condor_starter.std
STARTER_LOCAL       = $(SBIN)/condor_starter
STARTD_ADDRESS_FILE = $(LOG)/.startd_address
BenchmarkTimer = (CurrentTime - LastBenchmark)
RunBenchmarks : (LastBenchmark == 0 ) || ($(BenchmarkTimer) >= (4 * $(HOUR)))
CONSOLE_DEVICES = mouse, console
COLLECTOR_HOST_STRING = "$(COLLECTOR_HOST)"
STARTD_ATTRS = COLLECTOR_HOST_STRING
STARTD_JOB_EXPRS = ImageSize, ExecutableSize, JobUniverse, NiceUser
CKPT_PROBE = $(LIBEXEC)/condor_ckpt_probe
SHADOW_LIST = SHADOW, SHADOW_STANDARD
SHADOW          = $(SBIN)/condor_shadow
SHADOW_STANDARD     = $(SBIN)/condor_shadow.std
SCHEDD_ADDRESS_FILE = $(LOG)/.schedd_address
SCHEDD_DAEMON_AD_FILE = $(LOG)/.schedd_classad
SHADOW_SIZE_ESTIMATE    = 1800
QUEUE_SUPER_USERS   = root, condor
PROCD = $(SBIN)/condor_procd
PROCD_ADDRESS = $(LOCK)/procd_pipe
PROCD_MAX_SNAPSHOT_INTERVAL = 60
WINDOWS_SOFTKILL = $(SBIN)/condor_softkill
VALID_SPOOL_FILES   = job_queue.log, job_queue.log.tmp, history, \
                          Accountant.log, Accountantnew.log, \
                          local_univ_execute, .quillwritepassword, \
                          .pgpass
INVALID_LOG_FILES   = core
JAVA = /usr/bin/java
JAVA_MAXHEAP_ARGUMENT = -Xmx
JAVA_CLASSPATH_DEFAULT = $(LIB) $(LIB)/scimark2lib.jar .
JAVA_CLASSPATH_ARGUMENT = -classpath
JAVA_CLASSPATH_SEPARATOR = :
JAVA_BENCHMARK_TIME = 2
JAVA_EXTRA_ARGUMENTS =
GRIDMANAGER         = $(SBIN)/condor_gridmanager
GT2_GAHP            = $(SBIN)/gahp_server
GRID_MONITOR            = $(SBIN)/grid_monitor.sh
MAX_GRIDMANAGER_LOG = 1000000
GRIDMANAGER_DEBUG   =
GRIDMANAGER_LOG = $(LOG)/GridmanagerLog.$(USERNAME)
GRIDMANAGER_LOCK = $(LOCK)/GridmanagerLock.$(USERNAME)
GRIDMANAGER_MAX_JOBMANAGERS_PER_RESOURCE = 10
CRED_MIN_TIME_LEFT      = 120
ENABLE_GRID_MONITOR = TRUE
CONDOR_GAHP = $(SBIN)/condor_c-gahp
CONDOR_GAHP_WORKER = $(SBIN)/condor_c-gahp_worker_thread
MAX_C_GAHP_LOG  = 1000000
C_GAHP_LOG = /tmp/CGAHPLog.$(USERNAME)
C_GAHP_LOCK = /tmp/CGAHPLock.$(USERNAME)
C_GAHP_WORKER_THREAD_LOG = /tmp/CGAHPWorkerLog.$(USERNAME)
C_GAHP_WORKER_THREAD_LOCK = /tmp/CGAHPWorkerLock.$(USERNAME)
GT4_GAHP = $(SBIN)/gt4_gahp
GT4_LOCATION = $(LIB)/gt4
GT42_GAHP = $(SBIN)/gt42_gahp
GT42_LOCATION = $(LIB)/gt42
GRIDFTP_SERVER = $(LIBEXEC)/globus-gridftp-server
GRIDFTP_SERVER_WRAPPER = $(LIBEXEC)/gridftp_wrapper.sh
GLITE_LOCATION = $(LIB)/glite
PBS_GAHP = $(GLITE_LOCATION)/bin/batch_gahp
LSF_GAHP = $(GLITE_LOCATION)/bin/batch_gahp
UNICORE_GAHP = $(SBIN)/unicore_gahp
NORDUGRID_GAHP = $(SBIN)/nordugrid_gahp
AMAZON_GAHP = $(SBIN)/amazon_gahp
AMAZON_GAHP_LOG = /tmp/AmazonGahpLog.$(USERNAME)
GRIDMANAGER_JOB_PROBE_INTERVAL = 300
GRIDMANAGER_MAX_SUBMITTED_JOBS_PER_RESOURCE_AMAZON = 20
CREDD               = $(SBIN)/condor_credd
CREDD_ADDRESS_FILE  = $(LOG)/.credd_address
CREDD_PORT          = 9620
CREDD_ARGS          = -p $(CREDD_PORT) -f
CREDD_LOG           = $(LOG)/CredLog
CREDD_DEBUG         = D_FULLDEBUG
MAX_CREDD_LOG       = 4000000
CRED_STORE_DIR = $(LOCAL_DIR)/cred_dir
STORK               = $(SBIN)/stork_server
STORK_ADDRESS_FILE = $(LOG)/.stork_address
STORK_LOG_BASE      = $(LOG)/Stork
STORK_LOG = $(LOG)/StorkLog
STORK_DEBUG = D_FULLDEBUG
MAX_STORK_LOG = 4000000
STORK_PORT          = 9621
STORK_ARGS = -p $(STORK_PORT) -f -Serverlog $(STORK_LOG_BASE)
QUILL = $(SBIN)/condor_quill
QUILL_LOG = $(LOG)/QuillLog
QUILL_ADDRESS_FILE = $(LOG)/.quill_address
DBMSD = $(SBIN)/condor_dbmsd
DBMSD_ARGS = -f
DBMSD_LOG = $(LOG)/DbmsdLog
VM_GAHP_LOG = $(LOG)/VMGahpLog
MAX_VM_GAHP_LOG = 1000000
VMWARE_PERL = perl
VMWARE_SCRIPT = $(SBIN)/condor_vm_vmware.pl
VMWARE_NETWORKING_TYPE = nat
XEN_SCRIPT = $(SBIN)/condor_vm_xen.sh
LeaseManager            = $(SBIN)/condor_lease_manager
LeaseManger_ADDRESS_FILE    = $(LOG)/.lease_manager_address
LeaseManager_LOG        = $(LOG)/LeaseManagerLog
LeaseManager_DEBUG      = D_FULLDEBUG
MAX_LeaseManager_LOG        = 1000000
LeaseManager.GETADS_INTERVAL    = 60
LeaseManager.UPDATE_INTERVAL    = 300
LeaseManager.PRUNE_INTERVAL = 60
LeaseManager.DEBUG_ADS      = False
LeaseManager.CLASSAD_LOG    = $(SPOOL)/LeaseManagerState
SCHEDD_HOST = $(CONDOR_HOST)
"""
