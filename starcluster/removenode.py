#!/usr/bin/env python
import re
from starcluster.logger import log

def _remove_line_from_file(f, match):
    fcontents = f.read().splitlines()
    lines = []
    for line in fcontents:
        if match not in line:
            lines.append(line)
    return '\n'.join(lines)

def remove_from_etc_hosts(node, cluster):
    for n in cluster.running_nodes:
        if node.id == n.id:
            continue
        ehosts_file = n.ssh.remote_file('/etc/hosts','r')
        new_file = _remove_line_from_file(ehosts_file, node.private_dns_name)
        ehosts_file.close()
        ehosts_file = n.ssh.remote_file('/etc/hosts','w')
        ehosts_file.write(new_file)
        ehosts_file.close()

def remove_nfs_exports(master, node):
    exports_file = master.ssh.remote_file('/etc/exports','r')
    new_file = _remove_line_from_file(exports_file, node.private_dns_name)
    exports_file.close()
    exports_file = master.ssh.remote_file('/etc/exports','w')
    exports_file.write(new_file)
    exports_file.close()
    master.ssh.execute('exportfs -a')

def remove_from_sge(master, node):
    master.ssh.execute('source /etc/profile && qconf -shgrp @allhosts > /tmp/allhosts')
    hgrp_file = master.ssh.remote_file('/tmp/allhosts','r')
    contents = hgrp_file.read().splitlines()
    hgrp_file.close()
    c = []
    for line in contents:
        line = line.replace(node.private_dns_name,'')
        c.append(line)
    hgrp_file = master.ssh.remote_file('/tmp/allhosts_new','w')
    hgrp_file.writelines('\n'.join(c))
    hgrp_file.close()
    master.ssh.execute('source /etc/profile && qconf -Mhgrp /tmp/allhosts_new')
    master.ssh.execute('source /etc/profile && qconf -sq all.q > /tmp/allq')
    allq_file = master.ssh.remote_file('/tmp/allq','r')
    contents = allq_file.read()
    allq_file.close()
    c = [l.strip() for l in contents.splitlines()]
    s = []
    allq = []
    for l in c:
        if l.startswith('slots') or l.startswith('['):
            s.append(l)
        else:
            allq.append(l)
    regex = re.compile(r"\[%s=\d+\],?" % node.private_dns_name)
    slots = []
    for line in s:
        line = line.replace('\\','')
        slots.append(regex.sub('',line))
    allq.append(''.join(slots))
    f = master.ssh.remote_file('/tmp/allq_new','w')
    allq[-1] = allq[-1].strip()
    if allq[-1].endswith(','):
        allq[-1] = allq[-1][:-1]
    f.write('\n'.join(allq))
    f.close()
    master.ssh.execute('source /etc/profile && qconf -Mq /tmp/allq_new')
    master.ssh.execute('source /etc/profile && qconf -de %s' % node.private_dns_name)
    master.ssh.execute('source /etc/profile && qconf -dconf %s' % node.private_dns_name)

def remove_node(node, cluster):
    log.info("removing node %s, state = %s." % (node.id, node.state))
    m = cluster.master_node
    remove_from_sge(m, node)
    log.debug("removed from sge")
    remove_from_etc_hosts(node,cluster)
    log.debug("removed from etc hosts")
    remove_nfs_exports(m, node)
    log.debug("removed from nfs")
    node.stop()
    log.info("node %s stopped." % node.id)
