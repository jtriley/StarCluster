import posixpath

from starcluster import threadpool
from starcluster import clustersetup
from starcluster.logger import log

core_site_templ = """\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<!-- In: conf/core-site.xml -->
<property>
  <name>hadoop.tmp.dir</name>
  <value>%(hadoop_tmpdir)s</value>
  <description>A base for other temporary directories.</description>
</property>

<property>
  <name>fs.default.name</name>
  <value>hdfs://%(master)s:54310</value>
  <description>The name of the default file system.  A URI whose
  scheme and authority determine the FileSystem implementation.  The
  uri's scheme determines the config property (fs.SCHEME.impl) naming
  the FileSystem implementation class.  The uri's authority is used to
  determine the host, port, etc. for a filesystem.</description>
</property>

</configuration>
"""

hdfs_site_templ = """\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<!-- In: conf/hdfs-site.xml -->
<property>
  <name>dfs.permissions</name>
  <value>false</value>
</property>
<property>
  <name>dfs.replication</name>
  <value>%(replication)d</value>
  <description>Default block replication.
  The actual number of replications can be specified when the file is created.
  The default is used if replication is not specified in create time.
  </description>
</property>
</configuration>
"""

mapred_site_templ = """\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<!-- Put site-specific property overrides in this file. -->

<configuration>
<!-- In: conf/mapred-site.xml -->
<property>
  <name>mapred.job.tracker</name>
  <value>%(master)s:54311</value>
  <description>The host and port that the MapReduce job tracker runs
  at.  If "local", then jobs are run in-process as a single map
  and reduce task.
  </description>
</property>
</configuration>
"""


class Hadoop(clustersetup.ClusterSetup):
    """
    Configures Hadoop using Cloudera packages on StarCluster
    """

    def __init__(self, hadoop_tmpdir='/mnt/hadoop'):
        self.hadoop_tmpdir = hadoop_tmpdir
        self.hadoop_home = '/usr/lib/hadoop'
        self.hadoop_conf = '/etc/hadoop-0.20/conf.starcluster'
        self.empty_conf = '/etc/hadoop-0.20/conf.empty'
        self.centos_java_home = '/usr/lib/jvm/java'
        self.centos_alt_cmd = 'alternatives'
        self.ubuntu_javas = ['/usr/lib/jvm/java-6-sun/jre',
                             '/usr/lib/jvm/java-6-openjdk/jre']
        self.ubuntu_alt_cmd = 'update-alternatives'
        self._pool = None

    @property
    def pool(self):
        if self._pool is None:
            self._pool = threadpool.get_thread_pool(20, disable_threads=False)
        return self._pool

    def _get_java_home(self, node):
        # check for CentOS, otherwise default to Ubuntu 10.04's JAVA_HOME
        if node.ssh.isfile('/etc/redhat-release'):
            return self.centos_java_home
        for java in self.ubuntu_javas:
            if node.ssh.isdir(java):
                return java
        raise Exception("Cant find JAVA jre")

    def _get_alternatives_cmd(self, node):
        # check for CentOS, otherwise default to Ubuntu 10.04
        if node.ssh.isfile('/etc/redhat-release'):
            return self.centos_alt_cmd
        return self.ubuntu_alt_cmd

    def _setup_hadoop_user(self, node, user):
        node.ssh.execute('gpasswd -a %s hadoop' % user)

    def _install_empty_conf(self, node):
        node.ssh.execute('cp -r %s %s' % (self.empty_conf, self.hadoop_conf))
        alternatives_cmd = self._get_alternatives_cmd(node)
        cmd = '%s --install /etc/hadoop-0.20/conf ' % alternatives_cmd
        cmd += 'hadoop-0.20-conf %s 50' % self.hadoop_conf
        node.ssh.execute(cmd)

    def _configure_env(self, node):
        env_file_sh = posixpath.join(self.hadoop_conf, 'hadoop-env.sh')
        node.ssh.remove_lines_from_file(env_file_sh, 'JAVA_HOME')
        env_file = node.ssh.remote_file(env_file_sh, 'a')
        env_file.write('export JAVA_HOME=%s\n' % self._get_java_home(node))
        env_file.close()

    def _configure_mapreduce_site(self, node, cfg):
        mapred_site_xml = posixpath.join(self.hadoop_conf, 'mapred-site.xml')
        mapred_site = node.ssh.remote_file(mapred_site_xml)
        mapred_site.write(mapred_site_templ % cfg)
        mapred_site.close()

    def _configure_core(self, node, cfg):
        core_site_xml = posixpath.join(self.hadoop_conf, 'core-site.xml')
        core_site = node.ssh.remote_file(core_site_xml)
        core_site.write(core_site_templ % cfg)
        core_site.close()

    def _configure_hdfs_site(self, node, cfg):
        hdfs_site_xml = posixpath.join(self.hadoop_conf, 'hdfs-site.xml')
        hdfs_site = node.ssh.remote_file(hdfs_site_xml)
        hdfs_site.write(hdfs_site_templ % cfg)
        hdfs_site.close()

    def _configure_masters(self, node, master):
        masters_file = posixpath.join(self.hadoop_conf, 'masters')
        masters_file = node.ssh.remote_file(masters_file)
        masters_file.write(master.alias)
        masters_file.close()

    def _configure_slaves(self, node, node_aliases):
        slaves_file = posixpath.join(self.hadoop_conf, 'slaves')
        slaves_file = node.ssh.remote_file(slaves_file)
        slaves_file.write('\n'.join(node_aliases))
        slaves_file.close()

    def _setup_hdfs(self, node, user):
        self._setup_hadoop_dir(node, self.hadoop_tmpdir, 'hdfs', 'hadoop')
        mapred_dir = posixpath.join(self.hadoop_tmpdir, 'hadoop-mapred')
        self._setup_hadoop_dir(node, mapred_dir, 'mapred', 'hadoop')
        userdir = posixpath.join(self.hadoop_tmpdir, 'hadoop-%s' % user)
        self._setup_hadoop_dir(node, userdir, user, 'hadoop')
        hdfsdir = posixpath.join(self.hadoop_tmpdir, 'hadoop-hdfs')
        if not node.ssh.isdir(hdfsdir):
            node.ssh.execute("su hdfs -c 'hadoop namenode -format'")
        self._setup_hadoop_dir(node, hdfsdir, 'hdfs', 'hadoop')

    def _setup_dumbo(self, node):
        if not node.ssh.isfile('/etc/dumbo.conf'):
            f = node.ssh.remote_file('/etc/dumbo.conf')
            f.write('[hadoops]\nstarcluster: %s\n' % self.hadoop_home)
            f.close()

    def _configure_hadoop(self, master, nodes, user):
        log.info("Configuring Hadoop...")
        log.info("Adding user %s to hadoop group" % user)
        for node in nodes:
            self.pool.simple_job(self._setup_hadoop_user, (node, user),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        node_aliases = map(lambda n: n.alias, nodes)
        cfg = {'master': master.alias, 'replication': 3,
               'hadoop_tmpdir': posixpath.join(self.hadoop_tmpdir,
                                               'hadoop-${user.name}')}
        log.info("Installing configuration templates...")
        for node in nodes:
            self.pool.simple_job(self._install_empty_conf, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring environment...")
        for node in nodes:
            self.pool.simple_job(self._configure_env, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring MapReduce Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_mapreduce_site, (node, cfg),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring Core Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_core, (node, cfg),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring HDFS Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_hdfs_site, (node, cfg),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring masters file...")
        for node in nodes:
            self.pool.simple_job(self._configure_masters, (node, master),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring slaves file...")
        for node in nodes:
            self.pool.simple_job(self._configure_slaves, (node, node_aliases),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring HDFS...")
        for node in nodes:
            self.pool.simple_job(self._setup_hdfs, (node, user),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring dumbo...")
        for node in nodes:
            self.pool.simple_job(self._setup_dumbo, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _setup_hadoop_dir(self, node, path, user, group, permission="775"):
        if not node.ssh.isdir(path):
            node.ssh.mkdir(path)
        node.ssh.execute("chown -R %s:hadoop %s" % (user, path))
        node.ssh.execute("chmod -R %s %s" % (permission, path))

    def _start_datanode(self, node):
        node.ssh.execute('/etc/init.d/hadoop-0.20-datanode restart')

    def _start_tasktracker(self, node):
        node.ssh.execute('/etc/init.d/hadoop-0.20-tasktracker restart')

    def _start_hadoop(self, master, nodes):
        log.info("Starting namenode...")
        master.ssh.execute('/etc/init.d/hadoop-0.20-namenode restart')
        log.info("Starting secondary namenode...")
        master.ssh.execute('/etc/init.d/hadoop-0.20-secondarynamenode restart')
        for node in nodes:
            log.info("Starting datanode on %s..." % node.alias)
            self.pool.simple_job(self._start_datanode, (node,),
                                 jobid=node.alias)
        self.pool.wait()
        log.info("Starting jobtracker...")
        master.ssh.execute('/etc/init.d/hadoop-0.20-jobtracker restart')
        for node in nodes:
            log.info("Starting tasktracker on %s..." % node.alias)
            self.pool.simple_job(self._start_tasktracker, (node,),
                                 jobid=node.alias)
        self.pool.wait()

    def _open_ports(self, master):
        ports = [50070, 50030]
        ec2 = master.ec2
        for group in master.cluster_groups:
            for port in ports:
                has_perm = ec2.has_permission(group, 'tcp', port, port,
                                              '0.0.0.0/0')
                if not has_perm:
                    group.authorize('tcp', port, port, '0.0.0.0/0')

    def run(self, nodes, master, user, user_shell, volumes):
        try:
            self._configure_hadoop(master, nodes, user)
            self._start_hadoop(master, nodes)
            self._open_ports(master)
            log.info("Job tracker status: http://%s:50030" % master.dns_name)
            log.info("Namenode status: http://%s:50070" % master.dns_name)
        finally:
            self.pool.shutdown()
