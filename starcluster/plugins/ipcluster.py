"""
A starcluster plugin for running an IPython cluster
(requires IPython 0.13+)
"""
import json
import os
import time
import posixpath

from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster.utils import print_timing
from starcluster.clustersetup import DefaultClusterSetup

from starcluster.logger import log

IPCLUSTER_CACHE = os.path.join(static.STARCLUSTER_CFG_DIR, 'ipcluster')
CHANNEL_NAMES = (
    "control",
    "task",
    "notification",
    "mux",
    "iopub",
    "registration",
)

STARTED_MSG = """\
IPCluster has been started on %(cluster)s for user '%(user)s'.

To connect to cluster from your local machine use:

    >>> from IPython.parallel import Client
    >>> Client('%(connector_file)s', sshkey='%(key_location)s')

See the IPCluster plugin doc for usage details:
http://star.mit.edu/cluster/docs/latest/plugins/ipython.html
"""


class IPCluster(DefaultClusterSetup):
    """Start an IPython (>= 0.11) cluster

    Example config:

    [plugin ipcluster]
    setup_class = starcluster.plugins.ipcluster.IPCluster
    enable_notebook = True
    notebook_passwd = secret

    """
    def __init__(self, enable_notebook=False, notebook_passwd=None):
        super(IPCluster, self).__init__()
        self.enable_notebook = enable_notebook
        self.notebook_passwd = notebook_passwd or utils.generate_passwd(16)

    def _check_ipython_installed(self, node):
        has_ipy = node.ssh.has_required(['ipython', 'ipcluster'])
        if not has_ipy:
            log.error("IPython is not installed... skipping plugin")
        return has_ipy

    def _write_config(self, master, user, profile_dir):
        """Create cluster configuration files."""
        log.info("Writing IPython cluster config files")
        master.ssh.execute("rm -rf '%s'" % profile_dir)
        master.ssh.execute('ipython profile create')
        f = master.ssh.remote_file('%s/ipcontroller_config.py' % profile_dir)
        ssh_server = "@".join([user, master.public_dns_name])
        f.write('\n'.join([
            "c = get_config()",
            "c.HubFactory.ip='%s'" % master.private_ip_address,
            "c.IPControllerApp.ssh_server='%s'" % ssh_server,
            # "c.Application.log_level = 'DEBUG'",
            "",
        ]))
        f.close()
        f = master.ssh.remote_file('%s/ipengine_config.py' % profile_dir)
        f.write('\n'.join([
            "c = get_config()",
            "c.EngineFactory.timeout = 10",
            # Engines should wait a while for url files to arrive,
            # in case Controller takes a bit to start:
            "c.IPEngineApp.wait_for_url_file = 30",
            # "c.Application.log_level = 'DEBUG'",
            "",
        ]))
        f.close()
        f = master.ssh.remote_file('%s/ipython_config.py' % profile_dir)
        f.write('\n'.join([
            "c = get_config()",
            "try:",
            "    import msgpack",
            "except ImportError:",
            # use pickle if msgpack is unavailable
            "    c.Session.packer='pickle'",
            "else:",
            # use msgpack if we can, because it's fast
            "    c.Session.packer='msgpack.packb'",
            "    c.Session.unpacker='msgpack.unpackb'",
            "c.EngineFactory.timeout = 10",
            # Engines should wait a while for url files to arrive,
            # in case Controller takes a bit to start
            "c.IPEngineApp.wait_for_url_file = 30",
            # "c.Application.log_level = 'DEBUG'",
            "",
        ]))
        f.close()

    def _start_cluster(self, master, profile_dir):
        n_engines = max(1, master.num_processors - 1)
        log.info("Starting IPython cluster with %i engines on master"
                 % n_engines)
        # cleanup existing connection files, to prevent their use
        master.ssh.execute("rm -f %s/security/*.json" % profile_dir)
        master.ssh.execute("ipcluster start --n=%i --delay=5 --daemonize"
                           % n_engines)
        # wait for JSON file to exist
        json_filename = '%s/security/ipcontroller-client.json' % profile_dir
        log.info("Waiting for JSON connector file...",
                 extra=dict(__nonewline__=True))
        s = spinner.Spinner()
        s.start()
        try:
            found_file = False
            for i in range(30):
                if master.ssh.isfile(json_filename):
                    found_file = True
                    break
                time.sleep(1)
            if not found_file:
                raise ValueError(
                    "Timeout while waiting for the cluser json file: "
                    + json_filename)
        finally:
            s.stop()
        # retrieve JSON connection info
        if not os.path.isdir(IPCLUSTER_CACHE):
            log.info("Creating IPCluster cache directory: %s" %
                     IPCLUSTER_CACHE)
            os.makedirs(IPCLUSTER_CACHE)
        local_json = os.path.join(IPCLUSTER_CACHE,
                                  '%s-%s.json' % (master.parent_cluster,
                                                  master.region.name))
        log.info("Saving JSON connector file to '%s'" %
                 os.path.abspath(local_json))
        master.ssh.get(json_filename, local_json)
        connection_params = json.load(open(local_json, 'rb'))
        for channel in CHANNEL_NAMES:
            port = connection_params.get(channel)
            if port is not None:
                self._authorize_port(master, port, channel)

        return local_json

    def _start_notebook(self, master, user, profile_dir):
        log.info("Setting up IPython web notebook for user: %s" % user)
        user_cert = posixpath.join(profile_dir, '%s.pem' % user)
        ssl_cert = posixpath.join(profile_dir, '%s.pem' % user)
        if not master.ssh.isfile(user_cert):
            log.info("Creating SSL certificate for user %s" % user)
            ssl_subj = "/C=US/ST=SC/L=STAR/O=Dis/CN=%s" % master.dns_name
            master.ssh.execute(
                "openssl req -new -newkey rsa:4096 -days 365 "
                '-nodes -x509 -subj %s -keyout %s -out %s' %
                (ssl_subj, ssl_cert, ssl_cert))
        else:
            log.info("Using existing SSL certificate...")
        f = master.ssh.remote_file('%s/ipython_notebook_config.py' %
                                   profile_dir)
        notebook_port = 8888
        sha1py = 'from IPython.lib import passwd; print passwd("%s")'
        sha1cmd = "python -c '%s'" % sha1py
        sha1pass = master.ssh.execute(sha1cmd % self.notebook_passwd)[0]
        f.write('\n'.join([
            "c = get_config()",
            "c.IPKernelApp.pylab = 'inline'",
            "c.NotebookApp.certfile = u'%s'" % ssl_cert,
            "c.NotebookApp.ip = '*'",
            "c.NotebookApp.open_browser = False",
            "c.NotebookApp.password = u'%s'" % sha1pass,
            "c.NotebookApp.port = %d" % notebook_port,
        ]))
        f.close()
        master.ssh.execute_async("ipython notebook --no-browser")
        self._authorize_port(master, notebook_port, 'notebook')
        log.info("IPython notebook URL: https://%s:%s" %
                 (master.dns_name, notebook_port))
        log.info("The notebook password is: %s" % self.notebook_passwd)
        log.warn("Please check your local firewall settings if you're having "
                 "issues connecting to the IPython notebook",
                 extra=dict(__textwrap__=True))

    def _authorize_port(self, node, port, service_name, protocol='tcp'):
        group = node.cluster_groups[0]
        world_cidr = '0.0.0.0/0'
        port_open = node.ec2.has_permission(group, protocol, port,
                                            port, world_cidr)
        if not port_open:
            log.info("Authorizing tcp port %s on %s for: %s" %
                     (port, world_cidr, service_name))
            group.authorize('tcp', port, port, world_cidr)

    @print_timing("IPCluster")
    def run(self, nodes, master, user, user_shell, volumes):
        if not self._check_ipython_installed(master):
            return
        user_home = master.getpwnam(user).pw_dir
        profile_dir = posixpath.join(user_home, '.ipython', 'profile_default')
        master.ssh.switch_user(user)
        self._write_config(master, user, profile_dir)

        # Start the cluster and some engines on the master (leave 1
        # processor free to handle cluster house keeping)
        cfile = self._start_cluster(master, profile_dir)

        # Start engines on each of the non-master nodes
        non_master_nodes = [node for node in nodes if not node.is_master()]
        for node in non_master_nodes:
            self.pool.simple_job(self._start_engines, (node, user),
                                 jobid=node.alias)
        if len(non_master_nodes) > 0:
            self.pool.wait(len(non_master_nodes))

        if self.enable_notebook:
            self._start_notebook(master, user, profile_dir)
        log.info(STARTED_MSG % dict(cluster=master.parent_cluster,
                                       user=user, connector_file=cfile,
                                       key_location=master.key_location))
        master.ssh.switch_user('root')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
       if not self._check_ipython_installed(master):
           return
       self._start_engines(node, user)

    def _start_engines(self, node, user):
        n = node.num_processors
        log.info("Adding %i engines on %s to ipcluster" % (n, node.alias))
        node.ssh.switch_user(user)
        node.ssh.execute("ipcluster engines --n=%i --daemonize" % n)
        node.ssh.switch_user('root')


class IPClusterStop(DefaultClusterSetup):

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Shutting down IPython cluster")
        master.ssh.switch_user(user)
        master.ssh.execute("ipcluster stop")
        time.sleep(2)
        master.ssh.execute("pkill -f ipcontrollerapp.py",
                           ignore_exit_status=True)
        for node in nodes:
            node.ssh.execute("pkill -f ipengineapp.py",
                               ignore_exit_status=True)
        master.ssh.switch_user('root')
