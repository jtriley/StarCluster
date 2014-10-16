from completers import NodeCompleter


class CmdRecover(NodeCompleter):
    """
    recover [--remove] <cluster-tag>

    Calls recover_nodes on each plugins. For OGS, missing active nodes are put
    back in.

    Putting a node back in is the equivalent of running
    addnode -x -a <node-alias> <cluster-tag>.
    """

    names = ['recover']

    def addopts(self, parser):
        parser.add_option(
            "--reboot-interval", dest="reboot_interval", type="int",
            default=10, help="Delay in minutes beyond which a node is "
            "rebooted if it's still being unreachable via SSH. Defaults "
            "to 10.")
        parser.add_option(
            "--num_reboot_restart", dest="n_reboot_restart", type="int",
            default=False, help="Numbere of reboots after which a node "
            "is restarted (stop/start). Helpfull in case the issue comes from "
            "the hardware. If the node is a spot instance, it "
            "will be terminated instead since it cannot be stopped. Defaults "
            "to false.")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = args[0]

        cluster = self.cm.get_cluster(tag)
        cluster.recover(self.opts.reboot_interval, self.opts.n_reboot_restart)
