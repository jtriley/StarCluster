import os
import sys
import base64
import posixpath

import starcluster
from starcluster import utils
from starcluster import static
from starcluster.logger import log

from base import CmdBase


class CmdShell(CmdBase):
    """
    shell

    Load an interactive IPython shell configured for starcluster development

    The following objects are automatically available at the prompt:

        cfg - starcluster.config.StarClusterConfig instance
        cm - starcluster.cluster.ClusterManager instance
        ec2 - starcluster.awsutils.EasyEC2 instance
        s3 - starcluster.awsutils.EasyS3 instance

    All StarCluster modules are automatically imported in the IPython session
    along with all StarCluster dependencies (e.g. boto, paramiko, etc.)

    If the --ipcluster=CLUSTER (-p) is passed, the IPython session will be
    automatically be configured to connect to the remote CLUSTER using
    IPython's parallel interface (requires IPython 0.11+). In this mode you
    will have the following additional objects available at the prompt:

        ipcluster - starcluster.cluster.Cluster instance for the cluster
        ipclient - IPython.parallel.Client instance for the cluster
        ipview - IPython.parallel.client.view.DirectView for the cluster

    Here's an example of how to run a parallel map across all nodes in the
    cluster:

        [~]> ipclient.ids
        [0, 1, 2, 3]
        [~]> res = ipview.map_async(lambda x: x**30, range(8))
        [~]> print res.get()
        [0,
         1,
         1073741824,
         205891132094649L,
         1152921504606846976L,
         931322574615478515625L,
         221073919720733357899776L,
         22539340290692258087863249L]

    See IPython parallel docs for more details
    (http://ipython.org/ipython-doc/stable/parallel)
    """

    names = ['shell', 'sh']

    def _add_to_known_hosts(self, node):
        log.info("Configuring local known_hosts file")
        user_home = os.path.expanduser('~')
        khosts = os.path.join(user_home, '.ssh', 'known_hosts')
        if not os.path.isfile(khosts):
            log.warn("Unable to configure known_hosts: file does not exist")
            return
        contents = open(khosts).read()
        if node.dns_name not in contents:
            server_pkey = node.ssh.get_server_public_key()
            khostsf = open(khosts, 'a')
            if contents[-1] != '\n':
                khostsf.write('\n')
            name_entry = '%s,%s' % (node.dns_name, node.ip_address)
            khostsf.write(' '.join([name_entry, server_pkey.get_name(),
                                    base64.b64encode(str(server_pkey)), '\n']))
            khostsf.close()

    def addopts(self, parser):
        parser.add_option("-p", "--ipcluster", dest="ipcluster",
                          action="store", type="string", default=None,
                          metavar="CLUSTER", help="configure a parallel "
                          "IPython session on CLUSTER")

    def execute(self, args):
        local_ns = dict(cfg=self.cfg, ec2=self.ec2, s3=self.s3, cm=self.cm,
                        starcluster=starcluster)
        if self.opts.ipcluster:
            log.info("Loading parallel IPython library")
            try:
                from IPython.parallel import Client
            except ImportError, e:
                self.parser.error(
                    "Error loading parallel IPython:"
                    "\n\n%s\n\n"
                    "NOTE: IPython 0.11+ must be installed to use -p" % e)
            tag = self.opts.ipcluster
            cl = self.cm.get_cluster(tag)
            region = cl.master_node.region.name
            ipcluster_dir = os.path.join(static.STARCLUSTER_CFG_DIR,
                                         'ipcluster')
            local_json = os.path.join(ipcluster_dir,
                                      "%s-%s.json" % (tag, region))
            if not os.path.exists(local_json):
                user_home = cl.master_node.getpwnam(cl.cluster_user).pw_dir
                profile_dir = posixpath.join(user_home, '.ipython',
                                             'profile_default')
                json = posixpath.join(profile_dir, 'security',
                                      'ipcontroller-client.json')
                if cl.master_node.ssh.isfile(json):
                    log.info("Fetching connector file from cluster...")
                    os.makedirs(ipcluster_dir)
                    cl.master_node.ssh.get(json, local_json)
                else:
                    self.parser.error(
                        "IPython json file %s does not exist locally or on "
                        "the cluster. Make sure the ipcluster plugin has "
                        "been executed and completed successfully.")
            key_location = cl.master_node.key_location
            self._add_to_known_hosts(cl.master_node)
            log.info("Loading parallel IPython client and view")
            rc = Client(local_json, sshkey=key_location, packer='pickle')
            local_ns['Client'] = Client
            local_ns['ipcluster'] = cl
            local_ns['ipclient'] = rc
            local_ns['ipview'] = rc[:]
        modules = [(starcluster.__name__ + '.' + module, module)
                   for module in starcluster.__all__]
        modules += [('boto', 'boto'), ('paramiko', 'paramiko'),
                    ('workerpool', 'workerpool'), ('jinja2', 'jinja2')]
        for fullname, modname in modules:
            log.info('Importing module %s' % modname)
            try:
                __import__(fullname)
                local_ns[modname] = sys.modules[fullname]
            except ImportError, e:
                log.error("Error loading module %s: %s" % (modname, e))
        utils.ipy_shell(local_ns=local_ns)
