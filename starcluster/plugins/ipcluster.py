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

"""
A starcluster plugin for running an IPython cluster
(requires IPython 0.13+)
"""
import json
import os
import random
import time
import posixpath

from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster import exception
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
IPCluster has been started on %(cluster)s for user '%(user)s'
with %(n_engines)d engines on %(n_nodes)d nodes.

To connect to cluster from your local machine use:

from IPython.parallel import Client
client = Client('%(connector_file)s', sshkey='%(key_location)s')

See the IPCluster plugin doc for usage details:
http://star.mit.edu/cluster/docs/latest/plugins/ipython.html
"""


def _kill_cmd(iptype, keepalive_cluster_ids=(), tokill_cluster_ids=()):
    """Generate a bash command to kill running `iptype`
    processes where iptype is either "ipengineapp" or "ipcontrollerapp"
    and running processes were explicitly called with a --cluster-id param.

    if not given keepalive_cluster_ids or tokill_cluster_ids, cmd will
    kill all found pids that match the aforementioned search criteria

    if given keepalive_cluster_ids, cmd will kill all `iptype` processes
    except those with given cluster ids

    if given tokill_cluster_ids, cmd will kill only `iptype` process
    """
    assert iptype in ['ipengineapp', 'ipcontrollerapp']
    assert isinstance(keepalive_cluster_ids, list) or isinstance(
        keepalive_cluster_ids, tuple)
    assert not set(keepalive_cluster_ids).intersection(tokill_cluster_ids)
    tokill = '(%s)' % '|'.join(cid for cid in tokill_cluster_ids)
    keepalive = "(%s)" % '|'.join(cid for cid in keepalive_cluster_ids)
    if keepalive_cluster_ids:
        cols = '-23'  # kill pids in comm column 1
    else:
        cols = '-12'  # kill pids in comm column 3

    cmd = ('comm {cols} <(pgrep -f "{iptype}.* --cluster-id {tokill}" | sort)'
           ' <(pgrep -f "{iptype}.* --cluster-id {keepalive}" | sort)'
           ' | xargs --no-run-if-empty kill').format(
               cols=cols, iptype=iptype, keepalive=keepalive, tokill=tokill)
    return cmd


def _start_engines(node, user, cluster_id, n_engines=None,
                   kill_existing=False):
    """Launch IPython engines on the given node

    Start one engine per CPU except on master where 1 CPU is reserved for house
    keeping tasks when possible.

    If kill_existing is True AND (if they have a cluster-id in
    tokill_cluster_ids or if tokill_cluster_ids is empty),
    any running IPython engines on the same node
    are killed first

    """
    if n_engines is None:
        n_engines = node.num_processors
    node.ssh.switch_user(user)
    if kill_existing:
        node.ssh.execute(
            _kill_cmd('ipengineapp', tokill_cluster_ids=[cluster_id]),
            ignore_exit_status=True)
    node.ssh.execute("ipcluster engines --n=%i --cluster-id %s --daemonize"
                     % (n_engines, cluster_id))
    node.ssh.switch_user('root')


def _str_to_kls(kls_string):
    """Utility function to instantiate a class from a string such as
    ipcluster.ClusterID"""
    data = kls_string.split('.')
    module = '.'.join(data[:-1])
    kls = data[-1]
    kls = getattr(__import__(module, fromlist=[kls]), kls)
    return kls


class ClusterID(object):
    """This class defines the default strategy for
      - identifying the current cluster id
      - identifying active cluster ids that should not be killed
      - creating new cluster ids

      You would override the classmethods here if you wish to, say:
        - store the existing cluster-ids in redis
        - only kill cluster-ids with no active jobs, where you specify what
          active means
        - if you wish to manage multiple ipclusters, where each instance
          has engines that have imported different versions of your code base
          (ie code deploys)
    """
    @classmethod
    def current(self, master, user):
        """
        Finds the most recent cluster id defined in ipcontroller-XXXX-*.json
        """
        master.ssh.switch_user(user)
        user_home = master.getpwnam(user).pw_dir
        json_dir = posixpath.join(user_home, '.ipython', 'profile_default',
                                  'security')
        most_recent_json = master.ssh.execute(
            'ls -1tr %s | tail -n 1' % json_dir)[0]
        cluster_id = most_recent_json.split('-')[1]
        return cluster_id

    @classmethod
    def active(self, master, user):
        """
        Returns a list of cluster-ids that are active,
        and therefore should not be killed.  By default, nothing is active.
        """
        return []

    @classmethod
    def new(self):
        """ Create a new cluster-id """
        cluster_id = ''.join(chr(random.randint(97, 122)) for x in range(4))
        return cluster_id


class IPCluster(DefaultClusterSetup):
    """Start an IPython (>= 0.13) cluster

    Example config:

    [plugin ipcluster]
    setup_class = starcluster.plugins.ipcluster.IPCluster
    enable_notebook = True
    notebook_passwd = secret
    notebook_directory = /home/user/notebooks
    packer = pickle
    log_level = info

    """
    def __init__(self, enable_notebook=False, notebook_passwd=None,
                 notebook_directory=None, packer=None, log_level='INFO',
                 cluster_id_kls=ClusterID):
        super(IPCluster, self).__init__()
        if isinstance(enable_notebook, basestring):
            self.enable_notebook = enable_notebook.lower().strip() == 'true'
        else:
            self.enable_notebook = enable_notebook
        self.notebook_passwd = notebook_passwd or utils.generate_passwd(16)
        self.notebook_directory = notebook_directory
        self.log_level = log_level
        if packer not in (None, 'json', 'pickle', 'msgpack'):
            log.error("Unsupported packer: %s", packer)
            self.packer = None
        else:
            self.packer = packer
        if isinstance(cluster_id_kls, str):
            cluster_id_kls = _str_to_kls(cluster_id_kls)
        self.cluster_id_kls = cluster_id_kls

    def _check_ipython_installed(self, node):
        has_ipy = node.ssh.has_required(['ipython', 'ipcluster'])
        if not has_ipy:
            raise exception.PluginError("IPython is not installed!")
        return has_ipy

    def _write_config(self, master, user, profile_dir, cluster_id):
        """Create cluster configuration files and preserve existing json files.
        """
        log.info("Writing IPython cluster config files")
        master.ssh.execute('ipython profile create')

        f = master.ssh.remote_file('%s/ipcontroller_config.py' % profile_dir)
        ssh_server = "@".join([user,
                               self._get_addr(master)])
        f.write('\n'.join([
            "c = get_config()",
            "c.HubFactory.ip='%s'" % master.private_ip_address,
            "c.IPControllerApp.ssh_server='%s'" % ssh_server,
            "c.Application.log_level = '%s'" % self.log_level,
            "c.IPControllerApp.cluster_id = '%s'" % cluster_id,
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
            "c.Application.log_level = '%s'" % self.log_level,
            "c.IPEngineApp.cluster_id = '%s'" % cluster_id,
            "",
        ]))
        f.close()
        f = master.ssh.remote_file('%s/ipython_config.py' % profile_dir)
        f.write('\n'.join([
            "c = get_config()",
            "c.EngineFactory.timeout = 10",
            # Engines should wait a while for url files to arrive,
            # in case Controller takes a bit to start
            "c.IPEngineApp.wait_for_url_file = 30",
            "c.Application.log_level = '%s'" % self.log_level,
            "",
        ]))
        if self.packer == 'msgpack':
            f.write('\n'.join([
                "c.Session.packer='msgpack.packb'",
                "c.Session.unpacker='msgpack.unpackb'",
                "",
            ]))
        elif self.packer == 'pickle':
            f.write('\n'.join([
                "c.Session.packer='pickle'",
                "",
            ]))
        # else: use the slow default JSON packer
        f.close()

    def _get_addr(self, node):
        """Return first match of public dns, public ip, private dns, private ip
        This gives better compatibility in scenarios where public address info
        is non-existent, such as when using starcluster in AWS VPC"""
        addr = [getattr(node, attr)
                for attr in ('dns_name', 'ip_address',
                             'private_dns_name', 'private_ip_address')
                if getattr(node, attr)][0]
        return addr

    def _start_cluster(self, master, profile_dir, cluster_id):
        n_engines = max(1, master.num_processors - 1)
        log.info("Starting the IPython controller and %i engines on master"
                 % n_engines)

        _cmd = ("ipcluster start --n=%i --delay=5 --cluster-id %s"
                % (n_engines, cluster_id))
        _fps = ' '.join(os.path.join(profile_dir, subdir, "*%s*" % cluster_id)
                        for subdir in ['log', 'pid', 'security'])
        trapped_cmd = "/bin/bash -c \"trap 'rm {fps} ' EXIT ; {cmd}\"".format(
            fps=_fps, cmd=_cmd)
        master.ssh.execute(trapped_cmd, detach=True, silent=False)
        # wait for JSON file to exist
        json_filename = ('%s/security/ipcontroller-%s-client.json'
                         % (profile_dir, cluster_id))
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
                    "Timeout while waiting for the cluster json file: "
                    + json_filename)
        finally:
            s.stop()
        # copy to ipcontroller-client.json for backwards compatibility
        json_copy = os.path.join(profile_dir, 'security', 'ipcontroller-client.json')
        master.ssh.execute(('test -e {sym} && rm {sym}'
                            ' ; cp {json} {sym} ; touch {json}')
                           .format(sym=json_copy, json=json_filename))
        # Retrieve JSON connection info to make it possible to connect a local
        # client to the cluster controller
        if not os.path.isdir(IPCLUSTER_CACHE):
            log.info("Creating IPCluster cache directory: %s" %
                     IPCLUSTER_CACHE)
            os.makedirs(IPCLUSTER_CACHE)
        local_json = os.path.join(IPCLUSTER_CACHE,
                                  '%s-%s-%s.json' % (master.parent_cluster,
                                                     master.region.name,
                                                     cluster_id))
        master.ssh.get(json_filename, local_json)
        # Configure security group for remote access
        connection_params = json.load(open(local_json, 'rb'))
        # For IPython version 0.14+ the list of channel ports is explicitly
        # provided in the connector file
        channel_authorized = False
        for channel in CHANNEL_NAMES:
            port = connection_params.get(channel)
            if port is not None:
                self._authorize_port(master, port, channel)
                channel_authorized = True
        # For versions prior to 0.14, the channel port numbers are not given in
        # the connector file: let's open everything in high port numbers
        if not channel_authorized:
            self._authorize_port(master, (1000, 65535), "IPython controller")
        return local_json, n_engines

    def _start_notebook(self, master, user, profile_dir):
        log.info("Setting up IPython web notebook for user: %s" % user)
        user_cert = posixpath.join(profile_dir, '%s.pem' % user)
        ssl_cert = posixpath.join(profile_dir, '%s.pem' % user)
        if not master.ssh.isfile(user_cert):
            log.info("Creating SSL certificate for user %s" % user)
            ssl_subj = "/C=US/ST=SC/L=STAR/O=Dis/CN=%s" % (
                self._get_addr(master))
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
        if self.notebook_directory is not None:
            if not master.ssh.path_exists(self.notebook_directory):
                master.ssh.makedirs(self.notebook_directory)
            master.ssh.execute_async(
                "ipython notebook --no-browser --notebook-dir='%s'"
                % self.notebook_directory)
        else:
            master.ssh.execute_async("ipython notebook --no-browser")
        self._authorize_port(master, notebook_port, 'notebook')
        log.info("IPython notebook URL: https://%s:%s" %
                 (self._get_addr(master), notebook_port))
        log.info("The notebook password is: %s" % self.notebook_passwd)
        log.warn("Please check your local firewall settings if you're having "
                 "issues connecting to the IPython notebook",
                 extra=dict(__textwrap__=True))

    def _authorize_port(self, node, port, service_name, protocol='tcp'):
        group = node.cluster_groups[0]
        world_cidr = '0.0.0.0/0'
        if isinstance(port, tuple):
            port_min, port_max = port
        else:
            port_min, port_max = port, port
        port_open = node.ec2.has_permission(group, protocol, port_min,
                                            port_max, world_cidr)
        if not port_open:
            log.info("Authorizing tcp ports [%s-%s] on %s for: %s" %
                     (port_min, port_max, world_cidr, service_name))
            group.authorize('tcp', port_min, port_max, world_cidr)

    @print_timing("IPCluster")
    def run(self, nodes, master, user, user_shell, volumes):
        self._check_ipython_installed(master)
        user_home = master.getpwnam(user).pw_dir
        profile_dir = posixpath.join(user_home, '.ipython', 'profile_default')
        cluster_id = self.cluster_id_kls.new()
        log.info('Using new cluster-id: %s' % cluster_id)
        master.ssh.switch_user(user)
        self._write_config(master, user, profile_dir, cluster_id)
        # Start the cluster and some engines on the master (leave 1
        # processor free to handle cluster house keeping)
        cfile, n_engines_master = self._start_cluster(master, profile_dir,
                                                      cluster_id)
        # Start engines on each of the non-master nodes
        non_master_nodes = [node for node in nodes if not node.is_master()]
        for node in non_master_nodes:
            self.pool.simple_job(
                _start_engines, (node, user, cluster_id, node.num_processors),
                jobid=node.alias)
        n_engines_non_master = sum(node.num_processors
                                   for node in non_master_nodes)
        if len(non_master_nodes) > 0:
            log.info("Adding %d engines on %d nodes",
                     n_engines_non_master, len(non_master_nodes))
            self.pool.wait(len(non_master_nodes))
        if self.enable_notebook:
            self._start_notebook(master, user, profile_dir)
        n_engines_total = n_engines_master + n_engines_non_master
        log.info(STARTED_MSG % dict(cluster=master.parent_cluster,
                                    user=user, connector_file=cfile,
                                    key_location=master.key_location,
                                    n_engines=n_engines_total,
                                    n_nodes=len(nodes)))
        master.ssh.switch_user('root')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        cluster_id = self.cluster_id_kls.current(master, user)
        self._check_ipython_installed(node)
        n_engines = node.num_processors
        log.info("Adding %d engines on %s", n_engines, node.alias)
        _start_engines(node, user, cluster_id)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")


class IPClusterStop(DefaultClusterSetup):
    """Shutdown all the IPython processes of the cluster that are not marked as
    "active" by cluster_id_kls.active

    This plugin is meant to be run manually with:

      starcluster runplugin plugin_conf_name cluster_name

    """
    def __init__(self, cluster_id_kls=ClusterID):
        super(IPClusterStop, self).__init__()
        if isinstance(cluster_id_kls, str):
            cluster_id_kls = _str_to_kls(cluster_id_kls)
        self.cluster_id_kls = cluster_id_kls

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Shutting down IPython cluster")
        master.ssh.switch_user(user)
        master.ssh.execute("ipcluster stop", ignore_exit_status=True)
        time.sleep(2)
        log.info("Stopping IPython controller on %s", master.alias)

        keepalive_cluster_ids = self.cluster_id_kls.active(master, user)
        log.info(_kill_cmd('ipcontrollerapp', keepalive_cluster_ids))
        log.info(_kill_cmd('ipengineapp', keepalive_cluster_ids))

        master.ssh.execute(_kill_cmd('ipcontrollerapp', keepalive_cluster_ids),
                           ignore_exit_status=True)
        master.ssh.execute("pkill -f 'ipython notebook'",
                           ignore_exit_status=True)
        master.ssh.switch_user('root')
        log.info("Stopping IPython engines on %d nodes", len(nodes))
        for node in nodes:
            self.pool.simple_job(self._stop_engines,
                                 (node, user, keepalive_cluster_ids))
        self.pool.wait(len(nodes))

    def _stop_engines(self, node, user, keepalive_cluster_ids):
        node.ssh.switch_user(user)
        node.ssh.execute(_kill_cmd('ipengineapp', keepalive_cluster_ids),
                         ignore_exit_status=True)
        node.ssh.switch_user('root')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_add_node method not implemented")

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")


class IPClusterRestartEngines(DefaultClusterSetup):
    """Plugin to kill and restart all engines of the current IPython cluster

    This plugin can be useful to hard-reset all the engines, for instance
    to be sure to free all the used memory even when dealing with memory leaks
    in compiled extensions.

    This plugin is meant to be run manually with:

      starcluster runplugin plugin_conf_name cluster_name

    """
    def __init__(self, cluster_id_kls=ClusterID):
        super(IPClusterRestartEngines, self).__init__()
        if isinstance(cluster_id_kls, str):
            cluster_id_kls = _str_to_kls(cluster_id_kls)
        self.cluster_id_kls = cluster_id_kls

    def run(self, nodes, master, user, user_shell, volumes):
        n_total = 0
        cluster_id = self.cluster_id_kls.current(master, user)
        for node in nodes:
            n_engines = node.num_processors
            if node.is_master() and n_engines >= 2:
                n_engines -= 1
            self.pool.simple_job(
                _start_engines, (node, user, cluster_id, n_engines, True),
                jobid=node.alias)
            n_total += n_engines
        log.info("Restarting %d engines on %d nodes", n_total, len(nodes))
        self.pool.wait(len(nodes))

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_add_node method not implemented")

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")
