#!/usr/bin/env python

from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log


class TmuxControlCenter(ClusterSetup):
    """
    Starts a TMUX session on StarCluster configured with split panes for all
    nodes. This allows you to interactively run commands on all nodes and see
    all the output at once.
    """

    def _resize_pane(self, node, envname, pane, units, up=False):
        upordown = '-D %s' % units
        if up:
            upordown = '-D %s' % units
        cmd = 'tmux resize-pane -t %s:%s %s' % (envname, pane, upordown)
        return node.ssh.execute(cmd)

    def _split_window(self, node, envname, window='', vertical=False):
        cmd = 'tmux split-window'
        if vertical:
            cmd += ' -h'
        return node.ssh.execute('%s -t %s:%s' % (cmd, envname, window))

    def _has_session(self, node, envname):
        status = node.ssh.get_status('tmux has-session -t %s' % envname)
        return status == 0

    def _send_keys(self, node, envname, cmd, window=''):
        node.ssh.execute('tmux send-keys -t %s:%s "%s"' % (envname, window,
                                                           cmd))
        node.ssh.execute('tmux send-keys -t %s:%s "Enter"' % (envname, window))

    def _new_session(self, node, envname):
        node.ssh.execute('tmux new-session -d -s %s' % envname)

    def _kill_session(self, node, envname):
        node.ssh.execute('tmux kill-session -t %s' % envname)

    def _new_window(self, node, envname, title):
        node.ssh.execute('tmux new-window -n %s -t %s:' % (title, envname))

    def create_session(self, node, envname, num_windows=5):
        if not self._has_session(node, envname):
            self._new_session(node, envname)
        for i in range(1, num_windows):
            self._new_window(node, envname, i)

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Starting TMUX Control Center...")
        envname = 'starcluster'
        master.ssh.connect(username=user)
        num_nodes = len(nodes)
        self.create_session(master, envname, num_nodes)
        for i, node in enumerate(nodes):
            self._new_window(master, envname, i)
            self._send_keys(master, envname, 'ssh %s' % node.alias,
                            window=i)
        master.ssh.connect(username='root')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to TMUX Control Center" % node.alias)
        #user_home = node.getpwnam(user).pw_dir

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Removing %s from TMUX Control Center" % node.alias)
