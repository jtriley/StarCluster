import string
import random
import posixpath

from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log


class MPICH2Setup(ClusterSetup):

    MPD_HOSTS = '/etc/mpd.hosts'
    MPD_CONF = '/etc/mpd.conf'

    def _generate_secretword(self):
        log.info("Generating MPICH secretword")
        secretword = map(lambda x: x, string.ascii_lowercase + string.digits)
        random.shuffle(secretword)
        return ''.join(secretword)

    def run(self, nodes, master, user, shell, volumes):
        secretword = self._generate_secretword()
        aliases = map(lambda x: x.alias, nodes)
        for node in nodes:
            log.info("Installing mpich2 on node %s" % node.alias)
            node.ssh.execute("apt-get -y install mpich2")
            log.info("Configuring %s on node %s" % (self.MPD_HOSTS,
                                                    node.alias))
            mpd_hosts = node.ssh.remote_file(self.MPD_HOSTS, 'w')
            mpd_hosts.write('\n'.join(aliases))
            mpd_hosts.close()
            log.info("Configuring %s on node %s for root" % (self.MPD_CONF,
                                                             node.alias))
            mpd_conf = node.ssh.remote_file(self.MPD_CONF, 'w')
            mpd_conf.write("secretword=%s\n" % secretword)
            mpd_conf.chmod(0600)
            mpd_conf.close()
        user_home = master.getpwnam(user).pw_dir
        user_mpd_conf = posixpath.join(user_home, '.mpd.conf')
        log.info("Configuring %s for user %s" % (user_mpd_conf, user))
        secretword = self._generate_secretword()
        umpdconf = node.ssh.remote_file(user_mpd_conf)
        umpdconf.write("secretword=%s\n" % secretword)
        umpdconf.chmod(0600)
        umpdconf.close()
        log.info("Launching mpdboot for root")
        master.ssh.execute('mpdboot -f %s -n %d' % (self.MPD_HOSTS,
                                                    len(nodes)))
        log.info("Launching mpdboot for user %s" % user)
        master.ssh.execute("su -l -c 'mpdboot -f %s -n %d' %s" % \
                           (self.MPD_HOSTS, len(nodes), user))
