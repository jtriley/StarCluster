import time
from functools import partial
from starcluster.logger import log
from starcluster import utils
from starcluster.node import Node
from starcluster.node import NodeRecoveryManager


class StreamingNodeAdd(object):

    """
    Class specialized in adding nodes as a stream.

    Rather than having to wait at each step, push the unpropagated spots
    or instances through an initialization phases pipeline. The result is that
    as soon as a node is ready, it is added to the clusteri, cutting down
    the time waiting for other nodes to be up. This class is especially useful
    the more the nodes that are added at once.
    """

    def __init__(self, cluster, spots, instances, reboot_interval,
                 n_reboot_restart):
        assert bool(spots) != bool(instances), \
            "You must define either spots or instances"
        self.cluster = cluster
        self.unpropagated_spots = spots
        self.spots = []
        self.unpropagated_instances = instances
        self.instances = []
        self.reboot_interval = reboot_interval
        self.n_reboot_restart = n_reboot_restart
        self.instances_nrm = {}
        self.ready_instances = []

    def stream_unpropagated_spots(self):
        if not self.unpropagated_spots:
            return

        propagated_spot_ids, _ = self.cluster.ec2.check_for_propagation(
            spot_ids=[s.id for s in self.unpropagated_spots])
        self.unpropagated_spots = utils.filter_move(
            lambda s: s.id not in propagated_spot_ids,
            self.unpropagated_spots, self.spots)
        if self.unpropagated_spots:
            log.info("Still waiting for unpropagated spots:"
                     + str(self.unpropagated_spots))

    def stream_spots(self):
        if not self.spots:
            return

        instance_ids = []
        self.spots = self.cluster.get_spot_requests_or_raise(self.spots)
        self.spots = utils.filter_move(
            lambda s: s.state != 'active' or s.instance_id is None,
            self.spots, instance_ids, lambda s: s.instance_id)
        if instance_ids:
            log.info("Instance ids:" + str(instance_ids))
            for instance_id in instance_ids:
                self.unpropagated_instances.append(
                    UnpropagatedInstance(instance_id))
        if self.spots:
            self.spots = \
                self.cluster.ec2.cancel_stuck_spot_instance_request(self.spots)
        if self.spots:
            log.info("Still waiting for spots: " + str(self.spots))

    def stream_unpropagated_instances(self):
        if not self.unpropagated_instances:
            return

        _, propagated_instance_ids = self.cluster.ec2.check_for_propagation(
            instance_ids=[s.id for s in self. unpropagated_instances])
        self.unpropagated_instances = utils.filter_move(
            lambda i: i.id not in propagated_instance_ids,
            self.unpropagated_instances, self.instances)
        if self.unpropagated_instances:
            log.info("Still waiting for unpropagated instances: "
                     + str(self.unpropagated_instances))
        self.instances = self.cluster.get_nodes_or_raise(nodes=self.instances)

    def stream_update_nrm(self):
        for instance in self.instances:
            if instance not in self.instances_nrm:
                nrm_cls = partial(NodeRecoveryManager,
                                  reboot_interval=self.reboot_interval,
                                  n_reboot_restart=self.n_reboot_restart)
                if isinstance(instance, Node):
                    nrm = nrm_cls(instance)
                else:
                    nrm = nrm_cls(Node(instance, self.cluster.key_location))
                self.instances_nrm[instance] = nrm

    def stream_instances(self):
        if not self.instances:
            return

        ssh_up = self.cluster.pool.map(lambda i: i.is_up(), self.instances)
        zip_instances = utils.filter_move(
            lambda i: i[0].state != 'running' or not i[1],
            zip(self.instances, ssh_up), self.ready_instances,
            lambda i: i[0])
        self.instances = [i[0] for i in zip_instances]
        if self.instances:
            log.info("Still waiting for instances: " + str(self.instances))

    def stream_manage_reboots(self):
        dead_instances = []
        self.instances = \
            utils.filter_move(lambda i: self.instances_nrm[i].check(),
                              self.instances, dead_instances)
        for instance in dead_instances:
            del self.instances_nrm[instance]

    def stream_ready_instances(self):
        for ready_instance in self.ready_instances:
            log.info("Adding node: %s" % ready_instance.alias)
            up_nodes = filter(lambda n: n.is_up(), self.cluster.nodes)
            try:
                self.cluster.run_plugins(method_name="on_add_node",
                                         node=ready_instance, nodes=up_nodes)
                # success
                del self.instances_nrm[ready_instance]
            except:
                log.error("Failed to add node {}"
                          .format(ready_instance.alias), exc_info=True)
                if self.instances_nrm[ready_instance].handle_reboot():
                    # back to not ready list
                    self.instances.append(ready_instance)
                else:
                    # dead, delete
                    del self.instances_nrm[ready_instance]

    def run(self):
        """
        As soon as a new node is ready, run the add plugins commands over it.
        """
        interval = self.cluster.refresh_interval
        log.info("Waiting for one of the new nodes to be up "
                 "(updating every {}s)".format(interval))

        while True:
            self.ready_instances = []
            self.stream_unpropagated_spots()
            self.stream_spots()
            self.stream_unpropagated_instances()
            self.stream_update_nrm()
            self.stream_instances()
            self.stream_manage_reboots()
            self.stream_ready_instances()

            if any([self.unpropagated_spots, self.spots,
                    self.unpropagated_instances, self.instances]):
                if self.ready_instances:
                    # ready_instances means nodes were added, that took
                    # time so we should loop again now
                    continue
                log.info("{} Sleeping for {} seconds"
                         .format(utils.get_utc_now(), interval))
                time.sleep(interval)
            else:
                break


class UnpropagatedInstance(object):

    def __init__(self, id):
        self.id = id


def streaming_add(cluster, spots=None, instances=None, reboot_interval=10,
                  n_reboot_restart=False):
    if spots is None:
        spots = []
    if instances is None:
        instances = []
    sna = StreamingNodeAdd(cluster, spots, instances, reboot_interval,
                           n_reboot_restart)
    sna.run()
