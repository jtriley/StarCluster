# Copyright 2009-2014 Justin Riley
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
import copy

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
        current_batch_file_users = \
            self._get_newusers_batch_file(master, self._usernames, user_shell)
        new_users = self._usernames
        # Copy the user list before manipulating it
        copy_new_users = copy.deepcopy(new_users)
        # Get user map here of /etc/passwd
        current_user_map = master.get_user_map()
        for user in new_users:
            if user in current_user_map:
                if user == current_user_map[user][0]:
                    copy_new_users.remove(user)
            else:
                print "Adding User: %s" % user
        new_users = copy_new_users
        if len(new_users) == 0:
            print "No new users to add"
            exit(0)
        # Compare current batch file users to new the users, then
        # APPEND to /root/.users/users.txt
        batchfile_new_users = copy.deepcopy(new_users)
        current_batch_file_users_list = current_batch_file_users.splitlines()
        for current_batch_file_line in current_batch_file_users_list:
                current_batch_file_user = current_batch_file_line.split(':')[0]
                if current_batch_file_user in new_users:
                        batchfile_new_users.remove(current_batch_file_user)
        new_batch_file = \
            self._get_newusers_batch_file(master, batchfile_new_users,
                                          user_shell, add_new_users=True)
        if new_batch_file:
            log.info("User batch file updated")
        new_uid, new_gid = self._get_max_unused_user_id()
        for user in new_users:
            for node in nodes:
                node.add_user(user, uid=new_uid)
            new_uid = new_uid + 1
        log.info("Configuring passwordless ssh for %d cluster users"
                 % self._num_users)
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
        cluster_tag = master.cluster_groups[0].name.replace(
            static.SECURITY_GROUP_PREFIX, '')
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
                                 batch_file=None, add_new_users=False):
        batch_file = batch_file or self.BATCH_USER_FILE
        if master.ssh.isfile(batch_file) and not add_new_users:
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
        if add_new_users:
            bfile = master.ssh.remote_file(batch_file, 'a')
        else:
            bfile = master.ssh.remote_file(batch_file, 'w')
        bfile.write(bfilecontents)
        bfile.close()
        return bfilecontents

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        try:
                batch_user_list = []
                current_user_map = master.get_user_map()
                for user, username in current_user_map.iteritems():
                        batch_user_list.append(username)

                usernames = batch_user_list
        except:
                if usernames:
                        usernames = [user.strip() for user in
                                     usernames.split(',')]
        self._usernames = usernames
        newusers = self._get_newusers_batch_file(master, self._usernames,
                                                 user_shell)
        newusers_list = []
        # populate list
        for user in newusers.splitlines():
            line = user.split(':')
            newusers_list.append(line[0])

        self._num_users = len(newusers_list)
        log.info("Creating %d users on %s" % (self._num_users, node.alias))
        node.ssh.execute("echo -n '%s' | newusers" % newusers)
        log.info("Adding %s to known_hosts for %d users" %
                 (node.alias, self._num_users))

        pbar = self.pool.progress_bar.reset()
        pbar.maxval = self._num_users
        for i, user in enumerate(newusers_list):
            master.add_to_known_hosts(user, [node])
            pbar.update(i + 1)
        pbar.finish()
        self._setup_scratch(nodes=[node], users=newusers_list)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError('on_remove_node method not implemented')
