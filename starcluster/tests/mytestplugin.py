from starcluster.logger import log
from starcluster.clustersetup import ClusterSetup


class SetupClass(ClusterSetup):
    def __init__(self, my_arg, my_other_arg):
        log.debug("setupclass: my_arg = %s, my_other_arg = %s" % (my_arg,
                                                                 my_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y imagemagick')
            node.ssh.execute('echo "i ran foo" >> /tmp/iran')


class SetupClass2(ClusterSetup):
    def __init__(self, my_arg, my_other_arg):
        log.debug("setupclass2: my_arg = %s, my_other_arg = %s" %
                  (my_arg, my_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN2 :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y python-utidylib')
            node.ssh.execute('echo "i ran too foo" >> /tmp/iran')


class SetupClass3(ClusterSetup):
    def __init__(self, my_arg, my_other_arg, my_other_other_arg):
        msg = "setupclass3: my_arg = %s, my_other_arg = %s"
        msg += " my_other_other_arg = %s"
        log.debug(msg % (my_arg, my_other_arg, my_other_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN3 :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y python-boto')
            node.ssh.execute('echo "i ran also foo" >> /tmp/iran')
