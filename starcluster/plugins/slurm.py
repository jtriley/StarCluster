"""
StarCluster plugin to configure a cluster.
using the SLURM cluster scheduling/management system.
See: http://computing.llnl.gov/linux/slurm/

Author: Jharrod LaFon, OpenEye Scientific Software
http://www.eyesopen.com
"""
import starcluster
from ssh import SFTPError
from starcluster import clustersetup
from starcluster.templates import slurm
from starcluster.logger import log
from starcluster.utils import print_timing
from starcluster.exception import SSHError


class SlurmPlugin(clustersetup.DefaultClusterSetup):
    """
    This plugin installs SLURM (https://computing.llnl.gov)

    """

    # Packages needed by the SLURM controller
    slurm_master_packages = [
                              "libmysqlclient16",
                              "mysql-server",
                              "slurm-llnl-slurmdbd",
                              "slurm-llnl",
                              "slurm-llnl-doc",
                              "slurm-llnl-sview",
                              "slurm-llnl-basic-plugins"]

    # Packages needed by a SLURM compute node
    slurm_packages = [
                      "munge",
                      "libmunge2",
                      "slurm-llnl",
                      "slurm-llnl-basic-plugins"]

    # Commands needed to initialize munge
    munge_key_perm_commands = [
                          "chmod g-w /etc",
                          "chmod 0700 /etc/munge/",
                          "chown munge /etc/munge/munge.key",
                          "chmod 600 /etc/munge/munge.key",
                          "/etc/init.d/munge restart"]

    # Template for .my.cnf (mysql)
    mysql_cnf_template = \
    """
    [client]
    user = root
    password = %(dbpassword)s
    """

    # Commands needed to initialize MySQL
    slurm_mysql_commands = [
        "sed -i 's/127.0.0.1/%(master-private-ip)s/g' " \
            + "/etc/mysql/my.cnf",
        "/etc/init.d/mysql stop",
        "/etc/init.d/mysql start",
        "mysql -u root -e "
        "\"grant all on slurm_acct_db.* TO 'root'@'localhost'"
        " identified by '%(dbpassword)s' with grant option;\"",
        "mysql -u root -e "
        "\"grant all on slurm_acct_db.* TO 'root'@'%(master)s'"
        " identified by '%(dbpassword)s' with grant option;\""]

    # Commands to initialize slurm accounting
    slurm_sacctmgr_commands = [
        "sacctmgr add cluster %(cluster-name)s -i",
        "sacctmgr add account root -i"]

    # Command to add a user and account
    slurm_sacct_add_account = "sacctmgr add account %s -i"
    slurm_sacct_add_user = "sacctmgr add user %s account=%s -i"

    # Command to change MySQL root password
    mysqladmin_password_command = \
        "mysqladmin -u root password '%(dbpassword)s'"

    # Command to drain SLURM nodes
    scontrol_disable_master_command = "scontrol update nodename=%(master)s " \
        + " state=drain reason='excluded'"

    # Path to SLURM configuration file
    slurm_conf_file = "/etc/slurm-llnl/slurm.conf"

    # Path to SLURM Database Daemon configuration file
    slurmdbd_conf_file = "/etc/slurm-llnl/slurmdbd.conf"

    # Path to root MySQL configuration file
    mysql_conf_file = "/root/.my.cnf"

    # Path to log of packages installed by this plugin
    packages_installed_file = "/root/.slurm-apt-log"

    # Remote exceptions to check for
    remote_exceptions = (SSHError, SFTPError, IOError)

    def __init__(self,
                 compute_on_master=True,
                 dbpassword='abc123',
                 max_nodes=20,
                 slurm_conf_template=None,
                 fake_node_ip="192.168.254.254",
                 add_users=True,
                 user_file="/root/.users/users.txt"):
        """
        Constructor for the SLURM plugin.

        compute_on_master: True if master should also be a compute node.
        dbpassword: Password to be used for the MySQL DB.
        max_nodes: Maximum possible number of nodes (including master)
        slurm_conf_template: Template slurm.conf file.
        fake_node_ip: IP Address given to nodes which are not allocated.
        add_users: True if users created by 'createusers' plugin should
        be added to the SLURM account manager.
        user_file: File created by 'createusers' plugin.
        """
        self.key = None
        self.fake_node_ip = fake_node_ip
        self.compute_on_master = str(compute_on_master).lower() == "true"
        self.dbpassword = dbpassword
        self.max_nodes = max_nodes
        self.add_users = add_users
        self.user_file = user_file
        self.slurm_attributes = None

        # Check for user provided slurm.conf template
        if slurm_conf_template:
            self._read_slurm_conf_template(slurm_conf_template)
        else:
            self.slurm_conf_template = slurm.slurm_conf_template
        super(SlurmPlugin, self).__init__()

    @print_timing("Installing & Configuring SLURM")
    def run(self, *args, **kwargs):
        """
        Wrapper for function to run plugin
        """
        try:
            self._run(*args, **kwargs)
        except SlurmPluginError, e:
            log.error(str(e))
            return
        log.info("Your SLURM cluster is now configured.  ")
        log.info("See http://computing.llnl.gov/linux/slurm for documentation,")
        log.info("or see `man slurm`.")

    def _run(self, nodes, master, user, user_shell, volumes):
        """
        Run SLURM plugin.

        First configure the SLURM controller,
        then configure the SLURM compute nodes.
        The SLURM controller depends on:
        munge
        MySQL
        """
        # First setup fake nodes to have dummy IPs in /etc/hosts
        self._update_fake_entries_to_etc_hosts(master, nodes)

        # Configure the SLURM contoller
        self._configure_slurm_master(master, nodes)

        # Get the munge key
        self._read_munge_key(master)

        # Configure each SLURM compute node
        wait_count = 0
        for node in filter(lambda n: n.alias != master.alias, nodes):
            wait_count += 1
            self.pool.simple_job(self._configure_node, args=(master, node))
        self.pool.wait(numtasks=wait_count)
        self.pool.shutdown()

        # Check to see if computing is disabled on the SLURM controller
        if not self.compute_on_master:
            self._disable_compute_on_master(master)

        # Disable all fake nodes within SLURM
        self._disable_fake_nodes(master)

    def _read_slurm_conf_template(self, template_file):
        """
        Read and validate user provided slurm.conf template
        """
        try:
            template = open(template_file, "r")
            self.slurm_conf_template = template.read()
        except IOError, e:
            raise SlurmPluginError("Unable to open template file: " + str(e))
        try:
            self.slurm_conf_template % self.slurm_attributes
        except KeyError, e:
            raise SlurmPluginError("Invalid slurm.conf template: " + str(e))

    def _update_fake_entries_to_etc_hosts(self,
                                          master,
                                          nodes,
                                          removed_node=None):
        """
        Adds fake entries to the /etc/hosts file so that SLURM will
        allow oversubscription of resources.
        """
        log.debug("Updating fake /etc/hosts entries.")
        try:
            hosts_file = master.ssh.remote_file("/etc/hosts", "r").read()
        except self.remote_exceptions, e:
            raise RemoteCommandError("Unable to read /etc/hosts on master: "\
                                     + str(e))
        new_hosts_file = ""
        # All nodes are fake at first
        fake_nodes = ["node{:03d}".format(n) \
                      for n in xrange(1, self.max_nodes)]

        # Filter out all real nodes
        for node in nodes:
            fake_nodes = filter(lambda n: n != node.alias, fake_nodes)

        # Also, eliminate a recently removed node
        if removed_node:
            fake_nodes = filter(lambda n: n != removed_node.alias, fake_nodes)

        # Check each line of the hosts file for a fake node,
        # and get rid of them
        for line in hosts_file.split('\n'):
            if not any(x in line.split(" ") for x in fake_nodes):
                new_hosts_file += line + "\n"

        # Now add the correct number of fake nodes
        for x in fake_nodes:
            new_hosts_file += self.fake_node_ip + " " + x + "\n"
        if removed_node:
            new_hosts_file += self.fake_node_ip + " " + removed_node.alias
        log.debug("Writing new hosts file:" + new_hosts_file)
        self.fake_nodes = fake_nodes
        try:
            newfile = master.ssh.remote_file("/etc/hosts", "w")
            newfile.write(new_hosts_file)
            newfile.close()
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Unable to write /etc/hosts on master: " + str(e))

    def remove_from_etc_hosts(self, nodes):
        """
        Dummy function.

        The starcluster remove_from_etc_hosts conflicts with the behavior
        needed to create a hidden partition in SLURM.
        """
        pass

    def _configure_node(self, master, node):
        """
        Configure SLURM compute node.

        Uninstall SGE
        Install SLURM packages
        Configure munge
        Configure SLURM
        Start services
        """
        log.debug("Configuring SLURM node " + str(node))
        # Uninstall SGE
        self._uninstall_sge_worker(node)

        # Install SLURM packages
        self._install_slurm_compute(node)

        # Configure munge (write munge key, perms, etc)
        self._configure_munge_node(node)

        # Write slurm.conf
        self._configure_slurm_node(node)

        # Start SLURM service
        self._start_slurm_node(node)

    def on_add_node(self, *args, **kwargs):
        """
        Called whenever a compute node is added to the cluster.

        Configures the compute node and adds it to the SLURM partition.
        """
        try:
            self._on_add_node(*args, **kwargs)
        except SlurmPluginError, e:
            log.error(str(e))

    def _on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info("Adding " + new_node.alias + " to the SLURM partition")
        # Update /etc/hosts to remove the fake node entry for this node
        self._update_fake_entries_to_etc_hosts(master, nodes)

        # Gather attributes needed to write slurm.conf
        self._set_slurm_attributes(master, nodes)

        # Get the munge key
        self._read_munge_key(master)

        # Install packages, write config files, etc
        self._configure_node(master, new_node)

        # slurm.conf for each node needs to be update to show
        # the fake and real nodes in separate partitions
        for node in nodes:
            self._configure_slurm_node(node)

        # Restart SLURM
        self._restart_slurm(master)

        # Disable fake nodes in SLURM
        self._disable_fake_nodes(master)

        # Set the new node's status to IDLE
        try:
            master.ssh.execute(
                "scontrol update nodename=" + new_node.alias + " state=idle",
                raise_on_failure=True)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to update node state: " + str(e))

    def _force_restart_slurm(self, master):
        """
        Only call this function if `scontrol reconfigure` failed
        """
        log.debug("Force restarting SLURM.")
        try:
            master.ssh.execute("/etc/init.d/slurm-llnl stop",
                               raise_on_failure=True)
            master.ssh.execute("/etc/init.d/slurm-llnl start",
                               raise_on_failure=True)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to restart SLURM controller: " + str(e))

    def _restart_slurm(self, master):
        """
        Reconfigures the SLURM controller.
        """
        log.debug(master.alias + ": Restarting SLURM.")
        try:
            # Reads in the config file and updates its state
            master.ssh.execute("scontrol reconfigure",
                               silent=True,
                               raise_on_failure=True)
        except self.remote_exceptions:
            # If scontrol failed, use a hammer
            self._force_restart_slurm(master)

    def on_remove_node(self, *args, **kwargs):
        """
        Called whenever a compute node is removed from the cluster.

        Removes the node from the SLURM partition and
        restarts SLURM
        """
        try:
            self._on_remove_node(*args, **kwargs)
        except SlurmPluginError, e:
            log.error(str(e))

    def _on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        try:
            # Remove this nodes entry from /etc/hosts
            master.ssh.remove_lines_from_file('/etc/hosts', node.alias)
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Failed to remove node from hosts file: " + str(e))

        # Override StarCluster function that conflicts with the
        # behavior we need
        starcluster.node.Node.remove_from_etc_hosts = \
            self.remove_from_etc_hosts

        log.info("Removing " + node.alias + " from SLURM")

        # Rewrite /etc/hosts with the new real and fake nodes
        self._update_fake_entries_to_etc_hosts(
            master, filter(
                lambda n: n.alias != node.alias, nodes), removed_node=node)

        # Set the slurm attributes needed to write slurm.conf
        self._set_slurm_attributes(
            master, filter(lambda n: n.alias != node.alias, nodes))

        # Write slurm.conf for each node with the new partitions
        for node in filter(lambda n: n.alias != node.alias, nodes):
            self._configure_slurm_node(node)

        # Reconfigure the SLURM controller
        self._restart_slurm(master)

        # Disable the fake nodes in the SLURM partition
        self._disable_fake_nodes(master)

    @print_timing("Configuring SLURM controller")
    def _configure_slurm_master(self, master, nodes):
        """
        Configures SLURM on the SLURM controller (master).
        -SLURM packages are installed.
        -Munge is installed and configured.
        -MySQL is installed and configured.
        -SLURM service is started.
        """
        log.debug("Configuring SLURM master.")
        # Install SLURM controller packages
        self._install_slurm_master(master, nodes)

        # Write slurm.conf
        self._configure_slurm_node(master)

        # Write munge key, set perms
        self._configure_munge_master(master)

        # Write slurmdbd.conf
        self._configure_slurmdbd_master(master)

        # Start MySQL - must be up before SLURM
        self._start_mysql(master)

        # Set the root MySQL password
        self._set_mysql_password(master)

        # Set MySQL to bind to the master's internal IP
        self._configure_mysql_master(master)

        # Start the SLURM database daemon
        self._start_slurmdbd_master(master)

        # Start the SLURM controller
        self._start_slurm_node(master)

        # Configure the accounts
        self._configure_slurm_accounting(master)

    def _disable_fake_nodes(self, master):
        """
        Disables all fake nodes in the SLURM partitions
        """
        log.debug("Disabling fake nodes: " + str(self.fake_nodes))
        if not len(self.fake_nodes):
            return
        cmd = "scontrol update nodename=" + self.fake_nodes[0]
        for node in self.fake_nodes[1:]:
            cmd += "," + node
        cmd += " state=drain reason=fake"
        try:
            master.ssh.execute(cmd,
                               silent=True,
                               ignore_exit_status=True)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to update node state: " + str(e))

    def _disable_compute_on_master(self, master):
        """
        Disallows compute jobs to run on the master
        """
        log.info("Not using master as a compute node")
        try:
            master.ssh.execute(
                self.scontrol_disable_master_command % self.slurm_attributes)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to remove master node from compute partition: "\
                + str(e))

    def _configure_slurm_accounting(self, master):
        """
        Uses sacctmgr to configure SLURM accounting.
        """
        log.debug("Setting up SLURM accounting.")

        # Execute the commands to enable accounting
        for command in self.slurm_sacctmgr_commands:
            try:
                master.ssh.execute(
                    command % self.slurm_attributes,
                    ignore_exit_status=True)
            except self.remote_exceptions, e:
                # These commands will work the first time,
                #    and fail each time after.
                pass

            # Check to see if we need to add slurm accounting
            # entries for the users created by createusers plugin
            if not self.add_users:
                return
            try:
                userfile = master.ssh.remote_file(self.user_file, "r")
            except self.remote_exceptions, e:
                raise RemoteCommandError(
                    "Unable to read: " + self.user_file + ": " + str(e)
                )
            except self.remote_exceptions, e:
                log.warn("For SLURM accounting to be enabled, the createusers"
                " plugin needs to be run before the SLURM plugin. Accounting "
                " not enabled. Error: " + str(e))
                return
            user_list_file = userfile.read()
            user_list = []
            for line in user_list_file.split('\n'):
                user_list.append(line.split(':')[0])
            user_list = filter(lambda u: len(u) != 0, user_list)

            # For each user, add a group and user account to SLURM
            for user in user_list:
                try:
                    master.ssh.execute(
                        self.slurm_sacct_add_account % user,
                        ignore_exit_status=True,
                        silent=True
                    )
                    master.ssh.execute(
                        self.slurm_sacct_add_user % (user, user),
                        ignore_exit_status=True,
                        silent=True
                    )
                except self.remote_exceptions, e:
                    pass

    def _read_munge_key(self, master):
        """
        Reads the munge key in from the master node
        """
        log.debug("Reading munge key.")
        try:
            keyfile = master.ssh.remote_file("/etc/munge/munge.key", "r")
            self.key = keyfile.read()
            keyfile.close()
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Unable to read /etc/munge/munge.key: " + str(e))

    def _set_mysql_password(self, master):
        """
        Sets the root MySQL password
        """
        log.debug("Setting MySQL password.")
        try:
            master.ssh.execute(
                self.mysqladmin_password_command % self.slurm_attributes,
                raise_on_failure=True)
        except self.remote_exceptions, e:
            raise MySQLError("Unable to set MySQL Password: " + str(e))

    def _configure_mysql_master(self, master):
        """
        Executes the necessary mysql commands to allow
        SLURM to use mysql.
        """
        log.debug("Configuring MySQL server on " + master.alias)
        self._setup_mysql_cnf(master)

        # Execute each command needed to configure and start MySQL
        for command in self.slurm_mysql_commands:
            try:
                output = master.ssh.execute(
                    command % self.slurm_attributes,
                    raise_on_failure=True)
            except self.remote_exceptions, e:
                raise MySQLError(
                    "Unable to execute: " + command + ": " + str(e))

    def _configure_munge_master(self, master):
        """
        Configures munge on the SLURM controller (master).

        -Creates a munge key if it doesn't exist.
        -Sets permissions on the munge key
        -Records the key for configuring compute nodes.
        """
        log.debug("Configuring munge on " + master.alias)
        try:
            if not master.ssh.isfile("/etc/init.d/munge.key"):
                master.ssh.execute(
                    "/usr/sbin/create-munge-key -f",
                    raise_on_failure=True)

            # Set correct permissions
            for command in self.munge_key_perm_commands:
                master.ssh.execute(command,
                                   raise_on_failure=True)
        except self.remote_exceptions, e:
            raise MungeError("Unable to intialize munge key: " + str(e))

    def _configure_munge_node(self, node):
        """
        Configure munge on a node.
        -Stores the munge key copied from the SLURM controller.
        -Starts munge service
        """
        log.debug(node.alias + ": configuring munge.")

        # Create /etc/munge if it doesn't exist
        if not node.ssh.isdir("/etc/munge/"):
            try:
                node.ssh.mkdir("/etc/munge/", mode=0644)
            except self.remote_exceptions, e:
                raise MungeError("Unable to mkdir /etc/munge: " + str(e))

        # Write the munge key
        try:
            keyfile = node.ssh.remote_file("/etc/munge/munge.key", "w")
            keyfile.write(self.key)
            keyfile.close()
        except self.remote_exceptions, e:
            raise RemoteCommandError("Unable to write munge key: " + str(e))

        # Now set munge file permissions on this node
        for command in self.munge_key_perm_commands:
            try:
                node.ssh.execute(command, raise_on_failure=True)
            except self.remote_exceptions, e:
                raise MungeError(
                    "Node: " + node.alias + " Unable to initialize munge: "\
                    + str(e))

    def _install_slurm_compute(self, node):
        """
        Installs necessary packages for SLURM on a compute node.
        """
        log.debug(node.alias + ": installing SLURM.")

        # Install all necessary packages
        for package in self.slurm_packages:
            node.apt_install(package)

    def _set_slurm_attributes(self, master, nodes):
        """
        Sets the SLURM attributes for a cluster.
        -master is the hostname of the SLURM controller
        -cluster-name is the SLURM partition name (also StarCluster name)
        -nodelist is the list of compute nodes in the cluster
        """

        # List of nodes in the real partition
        partitionlist = ",".join(
                [n.alias for n in nodes])
        self.slurm_attributes = {
           "master": master.alias,
           "dbpassword": self.dbpassword,
           "master-private-ip": master.instance.private_ip_address,
           "cluster-name": master.cluster_groups[0].name.replace('@sc-', ''),
           "nodelist": ",".join([n.alias for n in nodes] + self.fake_nodes),
           "partitionlist": partitionlist,
           "fake-nodes": ",".join(self.fake_nodes)
           }

    def _install_slurm_master(self, master, nodes):
        """
        Installs the necessary SLURM packages on the SLURM controller.
        """
        log.debug("Installing SLURM on " + master.alias)

        # Set the slurm attributes
        self._set_slurm_attributes(master, nodes)

        # Check to see if the packages are already installed, exit if so
        try:
            already_installed = master.ssh.isfile(self.packages_installed_file)
        except self.remote_exceptions, e:
            raise RemoteCommandError("Unable to read file: " + \
                self.packages_installed_file + ": " + str(e))
        if already_installed:
            return

        # Make the log file
        try:
            log_file = master.ssh.remote_file(
                self.packages_installed_file, "w")
        except self.remote_exceptions, e:
            raise RemoteCommandError("Unable to open file: " + \
                self.packages_installed_file + ": " + str(e))
        log_file.write("# SLURM Plugin installed packages:\n")

        # Install the packages
        for package in self.slurm_master_packages + self.slurm_packages:
            log_file.write(str(package) + "\n")
            master.apt_install(package)
        log_file.close()

    def _setup_mysql_cnf(self, master):
        """
        Sets up a mysql.cnf file with the db
        password.
        """
        log.debug("Configuring mysql.cnf on " + master.alias)

        # Check to see if the file exists, exit if so
        try:
            if master.ssh.isfile(self.mysql_conf_file):
                return
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Couldn't read " + self.mysql_conf_file + ":" + str(e))

        log.debug("Writing " + self.mysql_conf_file)

        # Write the file
        try:
            conf = master.ssh.remote_file(self.mysql_conf_file, "w")
        except self.remote_exceptions, e:
            raise MySQLError(
                "Unable to open " + self.mysql_conf_file + ": " + str(e))
        conf.write(self.mysql_cnf_template % self.slurm_attributes)
        conf.close()

    def _configure_slurmdbd_master(self, master):
        """
        Writes out the SLURM configuration file on
        the SLURM controller.
        """
        log.debug(master.alias + ": Configuring slurmdbd")
        try:
            conf = master.ssh.remote_file(self.slurmdbd_conf_file, "w")
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Unable to open " + self.slurmdbd_conf_file + " for writing: "\
                + str(e))
        conf.write(slurm.slurmdbd_conf_template % self.slurm_attributes)
        conf.close()

    def _configure_slurm_node(self, node):
        """
        Configures SLURM on a SLURM compute node by writing
        out the configuration file.
        """
        log.debug(node.alias + ": Configuring SLURM.")
        try:
            conf = node.ssh.remote_file(self.slurm_conf_file, "w")
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Unable to open " + self.slurm_conf_file + ": " + str(e))

        # Write the file omitting master from the compute partition
        # if specified by user
        if not self.compute_on_master:
            conf.write(
                (self.slurm_conf_template \
                 + slurm.slurm_master_partition_template)
                       % self.slurm_attributes)

        # Otherwise include master
        else:
            conf.write(self.slurm_conf_template % self.slurm_attributes)
        conf.close()

    def _start_slurmdbd_master(self, master):
        """
        Starts the slurmdbd daemon on the master node.
        """
        log.debug("Restarting slurmdbd on " + master.alias)
        try:
            master.ssh.execute("/etc/init.d/slurm-llnl-slurmdbd stop")
            master.ssh.execute("/etc/init.d/slurm-llnl-slurmdbd start",
                               raise_on_failure=True)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to restart SLURM controller: " + str(e))

    def _start_mysql(self, node):
        """
        Starts the mysql service on the desired node.
        """
        log.debug("Restarting MySQL on " + node.alias)
        try:
            node.ssh.execute("/etc/init.d/mysql stop")
            node.ssh.execute("/etc/init.d/mysql start", raise_on_failure=True)
        except self.remote_exceptions, e:
            raise MySQLError("Unable to start MySQL server: " + str(e))

    def _start_slurm_node(self, node):
        """
        Starts the SLURM service.
        """
        log.debug(node.alias + ": starting SLURM service.")
        try:
            node.ssh.execute("/etc/init.d/slurm-llnl stop")
            node.ssh.execute("/etc/init.d/slurm-llnl start",
                             raise_on_failure=True)
        except self.remote_exceptions, e:
            raise SlurmError(
                "Unable to restart SLURM on " + node.alias + ": " + str(e))

    def _uninstall_sge_master(self, master):
        """
        Uninstall SGE from a master node.
        """
        log.debug("Removing SGE from " + master.alias)
        master.ssh.execute(
            'cd /opt/sge6/; echo y | /opt/sge6/inst_sge -ux all',
           ignore_exit_status=True)

    def _uninstall_sge_worker(self, node):
        """
        Uninstall SGE from a worker node.
        """
        log.debug("Removing SGE from " + node.alias)
        if not node.ssh.isdir('/opt/sge6'):
            log.debug('SGE already uninstalled.')
        else:
            node.ssh.execute('/opt/sge6/inst_sge -ux',
                             ignore_exit_status=True)


class SlurmPluginError(Exception):
    """
    Base class except for SlurmPlugin
    """
    pass


class RemoteCommandError(SlurmPluginError):
    """
    Indicates an error executing a remote command
    """

    def __init__(self, msg):
        self.msg = \
            "There was an error executing command on the cluster: " + msg
        super(RemoteCommandError, self).__init__()

    def __str__(self):
        return repr(self.msg)


class SlurmError(SlurmPluginError):
    """
    Indicates an error with the SLURM daemon (slurmd)
    """
    def __init__(self, msg):
        self.msg = "There was an error with a SLURM daemon: " + msg
        super(SlurmError, self).__init__()

    def __str__(self):
        return repr(self.msg)


class SlurmControllerError(SlurmPluginError):
    """
    Indicates an error with the SLURM controller (slurmcltd)
    """

    def __init__(self, msg):
        self.msg = \
        "There was an error with the SLURM controller.  Make sure " \
        + "that the SLURM controller daemon (slurmctld) is still "  \
        + "running on the master node. You can debug the daemon on "\
        + "the master node by running: slurmctld -D " \
        + "Error: " + msg
        super(SlurmControllerError, self).__init__()

    def __str__(self):
        return repr(self.msg)


class MungeError(SlurmPluginError):
    """
    Indicates and error with munge (munged)
    """

    def __init__(self, msg):
        self.msg = \
        "There was an error configuring munge.  SLURM requires munge for " \
        + "communication, and cannot function without.  Ensure that " \
        + "munge is installed and the NTP is correct on all nodes, and that " \
        + "the munge keys (/etc/munge/munge.key) match on all nodes. " \
        + " Error: " + msg
        super(MungeError, self).__init__()

    def __str__(self):
        return repr(self.msg)


class MySQLError(SlurmPluginError):
    """
    Indicates an error with the MySQL database
    """

    def __init__(self, msg):
        self.msg = \
        "There was an error with the MySQL server on the " \
        + "master node.  SLURM uses MySQL to store accounting and job data. " \
        + "Ensure that the database password is correct. " \
        + "Error: " + msg
        super(MySQLError, self).__init__()

    def __str__(self):
        return repr(self.msg)
