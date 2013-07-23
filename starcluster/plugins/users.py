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

import os
import posixpath

from starcluster import utils
from starcluster import static
from starcluster import exception
from starcluster import clustersetup
from starcluster.logger import log


class CreateUsers(clustersetup.DefaultClusterSetup):
    """
    Plugin for creating one or more cluster users
    """

    DOWNLOAD_KEYS_DIR = os.path.join(static.STARCLUSTER_CFG_DIR, 'user_keys')
    BATCH_USER_FILE = "/root/.users/users.txt"

    def __init__(self, num_users=None, usernames=None, download_keys=None,
                 download_keys_dir=None):
        if usernames:
            usernames = [user.strip() for user in usernames.split(',')]
        if num_users:
            try:
                num_users = int(num_users)
            except ValueError:
                raise exception.BaseException("num_users must be an integer")
        elif usernames:
            num_users = len(usernames)
        else:
            raise exception.BaseException(
                "you must provide num_users or usernames or both")
        if usernames and num_users and len(usernames) != num_users:
            raise exception.BaseException(
                "only %d usernames provided - %d required" %
                (len(usernames), num_users))
        self._num_users = num_users
        if not usernames:
            usernames = ['user%.3d' % i for i in range(1, num_users + 1)]
        self._usernames = usernames
        self._download_keys = str(download_keys).lower() == "true"
        self._download_keys_dir = download_keys_dir or self.DOWNLOAD_KEYS_DIR
        super(CreateUsers, self).__init__()

    def run(self, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Creating %d cluster users" % self._num_users)
        newusers = self._get_newusers_batch_file(master, self._usernames,
                                                 user_shell)
        for node in nodes:
            self.pool.simple_job(node.ssh.execute,
                                 ("echo '%s' | newusers" % newusers),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring passwordless ssh for %d cluster users" %
                 self._num_users)
        pbar = self.pool.progress_bar.reset()
        pbar.maxval = self._num_users
        for i, user in enumerate(self._usernames):
            master.generate_key_for_user(user, auth_new_key=True,
                                         auth_conn_key=True)
            master.add_to_known_hosts(user, nodes)
            pbar.update(i + 1)
        pbar.finish()
        self._setup_scratch(nodes, self._usernames)
        if self._download_keys:
            self._download_user_keys(master, self._usernames)

    def _download_user_keys(self, master, usernames):
        pardir = posixpath.dirname(self.BATCH_USER_FILE)
        bfile = posixpath.basename(self.BATCH_USER_FILE)
        if not master.ssh.isdir(pardir):
            master.ssh.makedirs(pardir)
        log.info("Tarring all SSH keys for cluster users...")
        for user in usernames:
            master.ssh.execute(
                "cp /home/%(user)s/.ssh/id_rsa %(keydest)s" %
                dict(user=user, keydest=posixpath.join(pardir, user + '.rsa')))
        cluster_tag = master.cluster_groups[0].name.replace('@sc-', '')
        tarfile = "%s-%s.tar.gz" % (cluster_tag, master.region.name)
        master.ssh.execute("tar -C %s -czf ~/%s . --exclude=%s" %
                           (pardir, tarfile, bfile))
        if not os.path.exists(self._download_keys_dir):
            os.makedirs(self._download_keys_dir)
        log.info("Copying cluster users SSH keys to: %s" %
                 os.path.join(self._download_keys_dir, tarfile))
        master.ssh.get(tarfile, self._download_keys_dir)
        master.ssh.unlink(tarfile)

    def _get_newusers_batch_file(self, master, usernames, shell,
                                 batch_file=None):
        batch_file = batch_file or self.BATCH_USER_FILE
        if master.ssh.isfile(batch_file):
            bfile = master.ssh.remote_file(batch_file, 'r')
            bfilecontents = bfile.read()
            bfile.close()
            return bfilecontents
        bfilecontents = ''
        tmpl = "%(username)s:%(password)s:%(uid)d:%(gid)d:"
        tmpl += "Cluster user account %(username)s:"
        tmpl += "/home/%(username)s:%(shell)s\n"
        shpath = master.ssh.which(shell)[0]
        ctx = dict(shell=shpath)
        base_uid, base_gid = self._get_max_unused_user_id()
        for user in usernames:
            home_folder = '/home/%s' % user
            if master.ssh.path_exists(home_folder):
                s = master.ssh.stat(home_folder)
                uid = s.st_uid
                gid = s.st_gid
            else:
                uid = base_uid
                gid = base_gid
                base_uid += 1
                base_gid += 1
            passwd = utils.generate_passwd(8)
            ctx.update(username=user, uid=uid, gid=gid, password=passwd)
            bfilecontents += tmpl % ctx
        pardir = posixpath.dirname(batch_file)
        if not master.ssh.isdir(pardir):
            master.ssh.makedirs(pardir)
        bfile = master.ssh.remote_file(batch_file, 'w')
        bfile.write(bfilecontents)
        bfile.close()
        return bfilecontents

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Creating %d users on %s" % (self._num_users, node.alias))
        newusers = self._get_newusers_batch_file(master, self._usernames,
                                                 user_shell)
        node.ssh.execute("echo '%s' | newusers" % newusers)
        log.info("Adding %s to known_hosts for %d users" %
                 (node.alias, self._num_users))
        pbar = self.pool.progress_bar.reset()
        pbar.maxval = self._num_users
        for i, user in enumerate(self._usernames):
            master.add_to_known_hosts(user, [node])
            pbar.update(i + 1)
        pbar.finish()
        self._setup_scratch(nodes=[node], users=self._usernames)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError('on_remove_node method not implemented')
