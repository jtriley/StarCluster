# Steps for mysql-cluster to work:
# 1. mkdir -p /var/lib/mysql-cluster/backup
# 2. chown -R mysql:mysql /var/lib/mysql-cluster/
# 3. generate ndb-mgmd for master
# 4. generate my.cnf for data nodes
# 5. /etc/init.d/mysql-ndb-mgm restart on master
# 6. pkill -9 mysql on data nodes
# 7. /etc/init.d/mysql start on data nodes
# 8. /etc/init.d/mysql-ndb restart on data nodes

# To run this plugin w/o 10.04 starcluster image:
# 1. starcluster sh
# 2. import mysqlcluster
# 3. create instance of plugin (t)
# 4. cl = cluster.get_cluster("test",cfg)
# 5. t.run(cl.master_node, cl.nodes, None, None, None)

# Correction to above, do this:
# 1. define plugin in config
# 2. start cluster mysql (will fail)
# 3. starcluster sh
# 4. cluster.run_plugin({plugin name},{cluster name},cfg)

from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log

ndb_mgmd_template = \
'''
[NDBD DEFAULT]
NoOfReplicas=%(num_replicas)s
DataMemory=%(data_memory)s    # How much memory to allocate for data storage
IndexMemory=%(index_memory)s   # How much memory to allocate for index storage
[MYSQLD DEFAULT]
[NDB_MGMD DEFAULT]
[TCP DEFAULT]
# Section for the cluster management node
[NDB_MGMD]
# IP address of the management node (this system)
HostName=%(mgm_ip)s
# Section for the storage nodes
'''

ndb_mgmd_storage = \
'''
[NDBD]
HostName=%(storage_ip)s
DataDir=%(data_dir)s
BackupDataDir=%(backup_data_dir)s
'''

my_cnf = \
'''
#
# The MySQL database server configuration file.
#
# You can copy this to one of:
# - "/etc/mysql/my.cnf" to set global options,
# - "~/.my.cnf" to set user-specific options.
#
# One can use all long options that the program supports.
# Run program with --help to get a list of available options and with
# --log.info-defaults to see which it would actually understand and use.
#
# For explanations see
# http://dev.mysql.com/doc/mysql/en/server-system-variables.html

# This will be passed to all mysql clients
# It has been reported that passwords should be enclosed with ticks/quotes
# escpecially if they contain "#" chars...
# Remember to edit /etc/mysql/debian.cnf when changing the socket location.
[client]
port            = 3306
socket          = /var/run/mysqld/mysqld.sock

# Here is entries for some specific programs
# The following values assume you have at least 32M ram

# This was formally known as [safe_mysqld]. Both versions are currently parsed.
[mysqld_safe]
socket          = /var/run/mysqld/mysqld.sock
nice            = 0

[mysqld]
#
# * Basic Settings
#

#
# * IMPORTANT
#   If you make changes to these settings and your system uses apparmor, you may
#   also need to also adjust /etc/apparmor.d/usr.sbin.mysqld.
#

user            = mysql
socket          = /var/run/mysqld/mysqld.sock
port            = 3306
basedir         = /usr
datadir         = /var/lib/mysql
tmpdir          = /tmp
skip-external-locking
#
# Instead of skip-networking the default is now to listen only on
# localhost which is more compatible and is not less secure.
bind-address            = 127.0.0.1
#
# * Fine Tuning
#
key_buffer              = 16M
max_allowed_packet      = 16M
thread_stack            = 192K
thread_cache_size       = 8
# This replaces the startup script and checks MyISAM tables if needed
# the first time they are touched
myisam-recover         = BACKUP
#max_connections        = 100
#table_cache            = 64
#thread_concurrency     = 10
#
# * Query Cache Configuration
#
query_cache_limit       = 1M
query_cache_size        = 16M
#
# * Logging and Replication
#
# Both location gets rotated by the cronjob.
# Be aware that this log type is a performance killer.
# As of 5.1 you can enable the log at runtime!
#general_log_file        = /var/log/mysql/mysql.log
#general_log             = 1

log_error                = /var/log/mysql/error.log

# Here you can see queries with especially long duration
#log_slow_queries       = /var/log/mysql/mysql-slow.log
#long_query_time = 2
#log-queries-not-using-indexes
#
# The following can be used as easy to replay backup logs or for replication.
# note: if you are setting up a replication slave, see README.Debian about
#       other settings you may need to change.
#server-id              = 1
#log_bin                        = /var/log/mysql/mysql-bin.log
expire_logs_days        = 10
max_binlog_size         = 100M
#binlog_do_db           = include_database_name
#binlog_ignore_db       = include_database_name
#
# * InnoDB
#
# InnoDB is enabled by default with a 10MB datafile in /var/lib/mysql/.
# Read the manual for more InnoDB related options. There are many!
#
# * Security Features
#
# Read the manual, too, if you want chroot!
# chroot = /var/lib/mysql/
#
# For generating SSL certificates I recommend the OpenSSL GUI "tinyca".
#
# ssl-ca=/etc/mysql/cacert.pem
# ssl-cert=/etc/mysql/server-cert.pem
# ssl-key=/etc/mysql/server-key.pem

# Cluster Configuration
ndbcluster
# IP address of management node
ndb-connectstring=%(mgm_ip)s

[mysqldump]
quick
quote-names
max_allowed_packet      = 16M

[mysql]
#no-auto-rehash # faster start of mysql but no tab completion

[isamchk]
key_buffer              = 16M

[MYSQL_CLUSTER]
ndb-connectstring=%(mgm_ip)s

#
# * IMPORTANT: Additional settings that can override those from this file!
#   The files must end with '.cnf', otherwise they'll be ignored.
#
!includedir /etc/mysql/conf.d/
'''

class MysqlCluster(ClusterSetup):
	def __init__(self,num_replicas,data_memory,index_memory,data_dir,backup_data_dir,\
					dedicated_query,num_data_nodes):
		self._num_replicas=num_replicas
		self._data_memory=data_memory
		self._index_memory=index_memory
		self._data_dir=data_dir
		self._backup_data_dir=backup_data_dir
		self._dedicated_query=dedicated_query
		self._num_data_nodes=num_data_nodes

	def run(self, master, nodes, user, user_shell, volumes):
		mconn = master.ssh
		# Get IPs for all nodes
		self.mgm_ip = master.private_ip_address
		if not self._dedicated_query: 
			self.storage_ips = [x.private_ip_address for x in nodes[1:]]
			self.query_ips = self.storage_ips
			self.data_nodes = nodes[1:]
			self.query_nodes = nodes
		else:
			self.data_nodes = nodes[1:self._num_data_nodes+1]
			self.query_nodes = nodes[self._num_data_nodes+1:]
			self.storage_ips = [x.private_ip_address for x in data_nodes]
			self.query_ips = [x.private_ip_address for x in query_nodes]

		# Create backup directory and change ownership of mysql-cluster directory
		for node in nodes:
			nconn = node.ssh
			node_num = nodes.index(node)
			if node_num == 0: node_num = 'master'
			log.info('Killing all mysql processes on node %s...' % node_num)
			nconn.execute('pkill -9 mysql', ignore_exit_status = True)
			log.info('Creating backup directory and changing ownership of ' +\
				'data directory on node %s' % node_num)
			nconn.execute('mkdir -p %s/BACKUP' % self._backup_data_dir)
			nconn.execute('chown -R mysql:mysql %s' % self._data_dir)
		
		# Generate and place ndb_mgmd configuration file
		log.info('Generating ndb_mgmd.cnf...')
		ndb_mgmd = mconn.remote_file('/etc/mysql/ndb_mgmd.cnf')
		ndb_mgmd.write(self.generate_ndb_mgmd())
		ndb_mgmd.close()
		
		# Generate and place my.cnf configuration file on each data node
		for node in nodes:
			log.info('Generating my.cnf on node %d' % nodes.index(node))
			nconn = node.ssh
			my_cnf = nconn.remote_file('/etc/mysql/my.cnf')
			my_cnf.write(self.generate_my_cnf())
			my_cnf.close()
		
		# Restart mysql-ndb-mgm on master
		log.info('Restarting mysql-ndb-mgm on master node...')
		mconn.execute('/etc/init.d/mysql-ndb-mgm restart')
		
		# Start mysqld-ndb on data nodes
		for node in self.data_nodes:
			nconn = node.ssh
			log.info('Restarting mysql-ndb on node %d...' % nodes.index(node))
			nconn.execute('/etc/init.d/mysql-ndb restart')
                
        # Start mysql on query nodes
		for node in self.query_nodes:
			nconn = node.ssh
			log.info('Starting mysql on node %d, ignoring missing file error...' % nodes.index(node))
			nconn.execute('/etc/init.d/mysql start', ignore_exit_status = True)
		
	def generate_ndb_mgmd(self):
		ndb_mgmd = ndb_mgmd_template % {'num_replicas':self._num_replicas,'data_memory':self._data_memory, \
			'index_memory':self._index_memory,'mgm_ip':self.mgm_ip}
		
		for x in self.storage_ips:
			ndb_mgmd += ndb_mgmd_storage % {'storage_ip':x,'data_dir':self._data_dir,\
				'backup_data_dir':self._backup_data_dir}
		
		ndb_mgmd += '\n'
		
		if self._dedicated_query: 
			for x in self.query_nodes:
				ndb_mgmd += '[MYSQLD]\nHostName=%s\n' % x.private_ip_address
		else:
			for x in self.query_nodes:
				ndb_mgmd += '[MYSQLD]\n'
			
		return ndb_mgmd
		
	def generate_my_cnf(self):
		return my_cnf % {'mgm_ip':self.mgm_ip}
