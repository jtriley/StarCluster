"""
A starcluster plugin for running an IPython cluster using SGE
(requires IPython 0.11+pyzmq or 0.10+twisted)

See ipythondev plugin for installing git master IPython and its dependencies
"""
import os
import time
import posixpath

from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster.utils import print_timing
from starcluster.clustersetup import ClusterSetup

from starcluster.logger import log

IPCLUSTER_CACHE = os.path.join(static.STARCLUSTER_CFG_DIR, 'ipcluster')

STARTED_MSG_10 = """\
IPCluster has been started on %(cluster)s for user '%(user)s'.

See the IPython 0.10.* parallel docs for usage details
(http://ipython.org/ipython-doc/rel-0.10.2/html/parallel)
"""


class IPCluster10(ClusterSetup):
    """
    Starts an IPCluster (0.10.*) on StarCluster
    """
    cluster_file = '/etc/clusterfile.py'
    log_file = '/var/log/ipcluster.log'

    def _create_cluster_file(self, master, nodes):
        engines = {}
        for node in nodes:
            engines[node.alias] = node.num_processors
        cfile = 'send_furl = True\n'
        cfile += 'engines = %s\n' % engines
        f = master.ssh.remote_file(self.cluster_file, 'w')
        f.write(cfile)
        f.close()

    def run(self, nodes, master, user, user_shell, volumes):
        self._create_cluster_file(master, nodes)
        log.info("Starting ipcluster...")
        master.ssh.execute(
            "su - %s -c 'screen -d -m ipcluster ssh --clusterfile %s'" %
            (user, self.cluster_file))
        log.info(STARTED_MSG_10 % dict(cluster=master.parent_cluster,
                                       user=user))

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to ipcluster" % node.alias)
        self._create_cluster_file(master, nodes)
        user_home = node.getpwnam(user).pw_dir
        furl_file = posixpath.join(user_home, '.ipython', 'security',
                                   'ipcontroller-engine.furl')
        node.ssh.execute(
            "su - %s -c 'screen -d -m ipengine --furl-file %s'" %
            (user, furl_file))

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Removing %s from ipcluster" % node.alias)
        less_nodes = filter(lambda x: x.id != node.id, nodes)
        self._create_cluster_file(master, less_nodes)
        node.ssh.execute('pkill ipengine')


STARTED_MSG_11 = """\
IPCluster has been started on %(cluster)s for user '%(user)s'.

See the IPCluster plugin doc for usage details:
http://web.mit.edu/starcluster/docs/latest/plugins/ipython.html
"""


class IPCluster11(ClusterSetup):
    """
    Start an IPython (0.11) cluster
    """
    def __init__(self, enable_notebook=False, notebook_passwd=None):
        self.enable_notebook = enable_notebook
        self.notebook_passwd = notebook_passwd or utils.generate_passwd(16)

    def _write_config(self, master, user, profile_dir):
        """
        Create cluster config
        """
        log.info("Writing IPython cluster config files")
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
        f = master.ssh.remote_file('%s/ipcluster_config.py' % profile_dir)
        f.write('\n'.join([
            "c = get_config()",
            "c.IPClusterStart.controller_launcher_class=" +
            "'SGEControllerLauncher'",
            # restrict controller to master node:
            "c.SGEControllerLauncher.queue='all.q@master'",
            "c.IPClusterEngines.engine_launcher_class='SGEEngineSetLauncher'",
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
            # in case Controller takes a bit to start via SGE
            "c.IPEngineApp.wait_for_url_file = 30",
            # "c.Application.log_level = 'DEBUG'",
            "",
        ]))
        f.close()

    def _start_cluster(self, master, n, profile_dir):
        log.info("Starting IPython cluster with %i engines" % n)
        # cleanup existing connection files, to prevent their use
        master.ssh.execute("rm -f %s/security/*.json" % profile_dir)
        master.ssh.execute("ipcluster start --n=%i --delay=5 --daemonize" % n,
                           source_profile=True)
        # wait for JSON file to exist
        json = '%s/security/ipcontroller-client.json' % profile_dir
        log.info("Waiting for JSON connector file...",
                 extra=dict(__nonewline__=True))
        s = spinner.Spinner()
        s.start()
        while not master.ssh.isfile(json):
            time.sleep(1)
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
        master.ssh.get(json, local_json)
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
        master.ssh.execute_async("ipython notebook")
        group = master.cluster_groups[0]
        world_cidr = '0.0.0.0/0'
        port_open = master.ec2.has_permission(group, 'tcp', notebook_port,
                                              notebook_port, world_cidr)
        if not port_open:
            log.info("Authorizing tcp port %s on %s" %
                     (notebook_port, world_cidr))
            group.authorize('tcp', notebook_port, notebook_port, world_cidr)
        log.info("IPython notebook URL: https://%s:%s" %
                 (master.dns_name, notebook_port))
        log.info("The notebook password is: %s" % self.notebook_passwd)

    @print_timing("IPCluster")
    def run(self, nodes, master, user, user_shell, volumes):
        n = sum([node.num_processors for node in nodes]) - 1
        user_home = node.getpwnam(user).pw_dir
        profile_dir = posixpath.join(user_home, '.ipython', 'profile_default')
        master.ssh.switch_user(user)
        self._write_config(master, user, profile_dir)
        cfile = self._start_cluster(master, n, profile_dir)
        if self.enable_notebook:
            self._start_notebook(master, user, profile_dir)
        log.info(STARTED_MSG_11 % dict(cluster=master.parent_cluster,
                                       user=user, connector_file=cfile,
                                       key_location=master.key_location))
        master.ssh.switch_user('root')

    def _stop_cluster(self, master, user):
        master.ssh.execute("pkill -f ipengineapp.py")
        master.ssh.execute("pkill -f ipcontrollerapp.py")

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        n = node.num_processors
        log.info("Adding %i engines on %s to ipcluster" % (n, node.alias))
        node.ssh.execute("ipcluster engines --n=%i --daemonize" % n,
                         source_profile=True)


class IPCluster(ClusterSetup):

    def __init__(self, enable_notebook=False, notebook_passwd=None):
        self.enable_notebook = enable_notebook
        self.notebook_passwd = notebook_passwd

    def _get_ipy_version(self, node):
        version_cmd = "python -c 'import IPython; print IPython.__version__'"
        return node.ssh.execute(version_cmd)[0]

    def _get_ipcluster_plugin(self, node):
        ipyversion = self._get_ipy_version(node)
        if ipyversion < '0.11':
            if not ipyversion.startswith('0.10'):
                log.warn("Trying unsupported IPython version %s" % ipyversion)
            return IPCluster10()
        else:
            return IPCluster11(self.enable_notebook, self.notebook_passwd)

    def _check_ipython_installed(self, node):
        has_ipy = node.ssh.has_required(['ipython', 'ipcluster'])
        if not has_ipy:
            log.error("IPython is not installed...skipping plugin")
        return has_ipy

    def run(self, nodes, master, user, user_shell, volumes):
        if not self._check_ipython_installed(master):
            return
        plug = self._get_ipcluster_plugin(master)
        plug.run(nodes, master, user, user_shell, volumes)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        if not self._check_ipython_installed(master):
            return
        plug = self._get_ipcluster_plugin(master)
        plug.on_add_node(node, nodes, master, user, user_shell, volumes)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        if not self._check_ipython_installed(master):
            return
        plug = self._get_ipcluster_plugin(master)
        plug.on_remove_node(node, nodes, master, user, user_shell, volumes)


class IPClusterStop(ClusterSetup):

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Shutting down IPython cluster")
        master.ssh.switch_user(user)
        master.ssh.execute("ipcluster stop", source_profile=True)
        time.sleep(2)
        master.ssh.execute("pkill -f ipcontrollerapp.py",
                           ignore_exit_status=True)
        for node in nodes:
            master.ssh.execute("pkill -f ipengineapp.py",
                               ignore_exit_status=True)
        master.ssh.switch_user('root')
