# Copyright 2017 Daniel Treiman
#

from starcluster import clustersetup
from starcluster.logger import log
from starcluster.templates import jupyterhub


class JupyterhubPlugin(clustersetup.DefaultClusterSetup):
    JUPYTERHUB_CONF = '/etc/jupyterhub/jupyterhub_conf.py'
    JUPYTERHUB_SERVICE = '/etc/systemd/system/jupyterhub.service'

    def __init__(self, homedir='/', notebook_dir=None, oauth_callback_url=None, oauth_client_id=None, oauth_client_secret=None,
                 hosted_domain=None, login_service=None, user_whitelist='', admin_whitelist='', queue=None, **kwargs):
        """Constructor.

        Args:
            homedir
            notebook_dir
            oauth_callback_url
            client_id
            client_secret
            hosted_domain
            login_service
            user_whitelist
            admin_whitelist
        """
        super(JupyterhubPlugin, self).__init__(**kwargs)
        self.homedir = homedir
        self.notebook_dir = homedir if notebook_dir is None else notebook_dir
        self.oauth_callback_url = oauth_callback_url
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.hosted_domain = hosted_domain
        self.login_service = login_service
        self.user_whitelist = user_whitelist.split(',')
        self.admin_whitelist = admin_whitelist.split(',')
        self.queue = queue

    def _setup_jupyterhub_node(self, node):
        node.ssh.execute('mkdir -p /run/user/1001/jupyter && chmod -R ugo+rwx /run/user/1001')

    def _write_jupyterhub_config(self, master):
        # Write jupyterhub.service
        jupyterhub_service = master.ssh.remote_file(self.JUPYTERHUB_SERVICE, 'w')
        jupyterhub_service.write(jupyterhub.jupyterhub_service_template % dict(jupyterhub_config=self.JUPYTERHUB_CONF))
        jupyterhub_service.close()
        # Write jupyterhub_conf.py
        jupyterhub_conf = master.ssh.remote_file(self.JUPYTERHUB_CONF, 'w')
        queue = ''
        if self.queue:
            queue = '-q ' + self.queue
        config_dict = dict(
            homedir=self.homedir,
            notebook_dir=self.notebook_dir,
            oauth_callback_url=self.oauth_callback_url,
            oauth_client_id=self.oauth_client_id,
            oauth_client_secret=self.oauth_client_secret,
            hosted_domain=repr(self.hosted_domain),
            login_service=repr(self.login_service),
            user_whitelist=','.join([repr(u) for u in self.user_whitelist]),
            admin_whitelist=','.join([repr(u) for u in self.admin_whitelist]),
            queue=queue
        )
        jupyterhub_conf.write(jupyterhub.jupyterhub_config_template % config_dict)
        jupyterhub_conf.close()

    def _setup_jupyterhub(self, master=None, nodes=None):
        log.info('Setting up Jupyterhub environment')
        master = master or self._master
        nodes = nodes or self.nodes
        log.info('Creating /etc/jupyterhub/jupyterhub_conf.py')
        self._write_jupyterhub_config(master)
        log.info('Starting Jupyterhub server')
        self._setup_jupyterhub_node(master)
        # Start jupyterhub process
        master.ssh.execute('systemctl start jupyterhub')
        log.info('Configuring Jupyter nodes')
        for node in nodes:
            self.pool.simple_job(self._setup_jupyterhub_node, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def run(self, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_jupyterhub()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info('Configuring %s for Jupyterhub' % node.alias)
        self._setup_jupyterhub_node(node)

    # Overrides DefaultClusterSetup on_remove_node to prevent double-teardown of hosts and NFS.
    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError('on_remove_node method not implemented')
