import pytest

from starcluster.plugins.sge import SGEPlugin
from starcluster.balancers import sge

live = pytest.mark.live


@live
def test_hostnames(nodes):
    for node in nodes:
        assert node.ssh.execute("hostname")[0] == node.alias


@live
def test_cluster_user(cluster, nodes):
    for node in nodes:
        assert cluster.cluster_user in node.get_user_map()


@live
def test_scratch_dirs(cluster, nodes):
    for node in nodes:
        assert node.ssh.isdir("/scratch")
        assert node.ssh.isdir("/scratch/%s" % cluster.cluster_user)


@live
def test_etc_hosts(cluster, nodes):
    for node in nodes:
        with node.ssh.remote_file('/etc/hosts', 'r') as rf:
            etc_hosts = rf.read()
            for snode in nodes:
                hosts_entry = snode.get_hosts_entry()
                assert hosts_entry in etc_hosts


@live
def test_nfs(nodes):
    for node in nodes[1:]:
        mmap = node.get_mount_map()
        assert 'master:/home' in mmap
        assert 'master:/opt/sge6' in mmap


@live
def test_passwordless_ssh(nodes):
    for node in nodes:
        for snode in nodes:
            resp = node.ssh.execute("ssh %s hostname" % snode.alias)[0]
            assert resp == snode.alias


@live
def test_sge(cluster, nodes):
    master_is_exec_host = True
    for plugin in cluster.plugins:
        if isinstance(plugin, SGEPlugin):
            master_is_exec_host = plugin.master_is_exec_host
    s = sge.SGEStats()
    qhost_xml = cluster.master_node.ssh.execute("qhost -xml")
    qhosts = s.parse_qhost('\n'.join(qhost_xml))
    qhost_aliases = [h['name'] for h in qhosts]
    for node in nodes:
        if not master_is_exec_host and node.alias == 'master':
            continue
        assert node.alias in qhost_aliases
