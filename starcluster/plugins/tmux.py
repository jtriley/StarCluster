from starcluster import utils
from starcluster import exception
from starcluster import clustersetup
from starcluster.logger import log


class TmuxControlCenter(clustersetup.DefaultClusterSetup):
    """
    Starts a TMUX session on StarCluster configured with split panes for all
    nodes. This allows you to interactively run commands on all nodes and see
    all the output at once.
    """
    _layouts = ['even-horizontal', 'even-vertical', 'main-horizontal',
                'main-vertical', 'tiled']

    def __init__(self, envname="starcluster"):
        self._envname = envname
        self._nodes = None
        self._master = None
        self._user = None
        self._user_shell = None
        self._volumes = None

    def _supports_layout(self, node, envname, layout, window=''):
        if layout not in self._layouts:
            raise exception.PluginError("unknown layout (options: %s)" %
                                        ", ".join(self._layouts))
        return self._select_layout(node, envname, layout, window) == 0

    def _select_layout(self, node, envname, layout="main-vertical", window=''):
        if layout not in self._layouts:
            raise exception.PluginError("unknown layout (options: %s)" %
                                          ", ".join(self._layouts))
        cmd = 'tmux select-layout -t %s:%s %s'
        return node.ssh.get_status(cmd % (envname, window, layout))

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

    def _rename_window(self, node, envname, window, name):
        cmd = 'tmux rename-window -t %s:%s %s' % (envname, window, name)
        return node.ssh.execute(cmd)

    def _has_session(self, node, envname):
        status = node.ssh.get_status('tmux has-session -t %s' % envname)
        return status == 0

    def _send_keys(self, node, envname, cmd, window=''):
        node.ssh.execute('tmux send-keys -t %s:%s "%s"' % (envname, window,
                                                           cmd))
        node.ssh.execute('tmux send-keys -t %s:%s "Enter"' % (envname, window))

    def _new_session(self, node, envname):
        node.ssh.execute('tmux new-session -d -s %s' % envname, detach=True)

    def _kill_session(self, node, envname):
        node.ssh.execute('tmux kill-session -t %s' % envname)

    def _kill_window(self, node, envname, window):
        node.ssh.execute('tmux kill-window -t %s:%s' % (envname, window))

    def _new_window(self, node, envname, title):
        node.ssh.execute('tmux new-window -n %s -t %s:' % (title, envname))

    def _select_window(self, node, envname, window=''):
        node.ssh.execute('tmux select-window -t %s:%s' % (envname, window))

    def _select_pane(self, node, envname, window, pane):
        node.ssh.execute('tmux select-pane -t %s:%s.%s' %
                         (envname, window, pane))

    def create_session(self, node, envname, num_windows=5):
        if not self._has_session(node, envname):
            self._new_session(node, envname)
        for i in range(1, num_windows):
            self._new_window(node, envname, i)

    def setup_tmuxcc(self, client=None, nodes=None, user='root',
                     layout='tiled'):
        log.info("Creating TMUX Control Center for user '%s'" % user)
        client = client or self._master
        nodes = nodes or self._nodes
        envname = self._envname
        orig_user = client.ssh._username
        if orig_user != user:
            client.ssh.connect(username=user)
        chunks = [chunk for chunk in utils.chunk_list(nodes, items=8)]
        num_windows = len(chunks) + len(nodes)
        if len(nodes) == 0:
            log.error("Cluster has no nodes, exiting...")
            return
        self.create_session(client, envname, num_windows=num_windows)
        if len(nodes) == 1 and client == nodes[0]:
            return
        if not self._supports_layout(client, envname, layout, window=0):
            log.warn("failed to select layout '%s', defaulting to "
                     "'main-vertical'" % layout)
            layout = "main-vertical"
            status = self._select_layout(client, envname, layout, window=0)
            if status != 0:
                raise exception.PluginError("failed to set a layout")
        for i, chunk in enumerate(chunks):
            self._rename_window(client, envname, i, 'all%s' % i)
            for j, node in enumerate(chunk):
                if j != 0:
                    self._split_window(client, envname, i)
                self._select_layout(client, envname, window=i, layout=layout)
                if node.alias != client.alias:
                    self._send_keys(client, envname, cmd='ssh %s' % node.alias,
                                    window="%d.%d" % (i, j))
        for i, node in enumerate(nodes):
            window = i + len(chunks)
            self._rename_window(client, envname, window, node.alias)
            if node.alias != client.alias:
                self._send_keys(client, envname, cmd='ssh %s' % node.alias,
                                window=window)
        self._select_window(client, envname, window=0)
        self._select_pane(client, envname, window=0, pane=0)
        if orig_user != user:
            client.ssh.connect(username=orig_user)

    def add_to_utmp_group(self, client, user):
        """
        Adds user (if exists) to 'utmp' group (if exists)
        """
        try:
            client.add_user_to_group(user, 'utmp')
        except exception.BaseException:
            pass

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Starting TMUX Control Center...")
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self.add_to_utmp_group(master, user)
        self.setup_tmuxcc(user='root')
        self.setup_tmuxcc(user=user)

    def _add_to_tmuxcc(self, client, node, user='root'):
        orig_user = client.ssh._username
        if orig_user != user:
            client.ssh.connect(username=user)
        self._new_window(client, self._envname, node.alias)
        self._send_keys(client, self._envname, cmd='ssh %s' % node.alias,
                        window=node.alias)
        if orig_user != user:
            client.ssh.connect(username=orig_user)

    def _remove_from_tmuxcc(self, client, node, user='root'):
        orig_user = client.ssh._username
        if orig_user != user:
            client.ssh.connect(username=user)
        self._kill_window(client, self._envname, node.alias)
        if orig_user != user:
            client.ssh.connect(username=orig_user)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to TMUX Control Center" % node.alias)
        self._add_to_tmuxcc(master, node, user='root')
        self._add_to_tmuxcc(master, node, user=user)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Removing %s from TMUX Control Center" % node.alias)
        self._remove_from_tmuxcc(master, node, user='root')
        self._remove_from_tmuxcc(master, node, user=user)
