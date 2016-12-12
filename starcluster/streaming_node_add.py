# Copyright 2014 Francois-Michel L'Heureux
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

    def stream_unpropagated_spots(self):
        if not self.unpropagated_spots:
            return

        propagated_spot_ids = self.cluster.ec2.get_propagated_spots(
            [s.id for s in self.unpropagated_spots])
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

        propagated_instance_ids = self.cluster.ec2.get_propagated_instances(
            [s.id for s in self. unpropagated_instances])
        self.unpropagated_instances = utils.filter_move(
            lambda i: i.id not in propagated_instance_ids,
            self.unpropagated_instances, self.instances)
        if self.unpropagated_instances:
            log.info("Still waiting for unpropagated instances: "
                     + str(self.unpropagated_instances))
        self.instances = self.cluster.get_nodes_or_raise(nodes=self.instances)

    def stream_update_nrm(self):
        for instance in self.instances:
            if instance.id not in self.instances_nrm:
                nrm_cls = partial(NodeRecoveryManager,
                                  reboot_interval=self.reboot_interval,
                                  n_reboot_restart=self.n_reboot_restart)
                if isinstance(instance, Node):
                    nrm = nrm_cls(instance)
                else:
                    nrm = nrm_cls(Node(instance, self.cluster.key_location))
                self.instances_nrm[instance.id] = nrm

    def stream_instances(self, ready_instances):
        if not self.instances:
            return

        ssh_up = self.cluster.pool.map(lambda i: i.is_up(), self.instances)
        zip_instances = utils.filter_move(
            lambda i: i[0].state != 'running' or not i[1],
            zip(self.instances, ssh_up), ready_instances,
            lambda i: i[0])
        self.instances = [i[0] for i in zip_instances]
        if self.instances:
            log.info("Still waiting for instances: " + str(self.instances))

    def stream_manage_reboots(self):
        dead_instances = []
        self.instances = \
            utils.filter_move(lambda i: self.instances_nrm[i.id].check(),
                              self.instances, dead_instances)
        for instance in dead_instances:
            del self.instances_nrm[instance.id]

    def stream_ready_instances(self, ready_instances):
        for ready_instance in ready_instances:
            log.info("Adding node: %s" % ready_instance.alias)
            up_nodes = filter(lambda n: n.is_up(), self.cluster.nodes)
            try:
                self.cluster.run_plugins(method_name="on_add_node",
                                         node=ready_instance, nodes=up_nodes)
                # success
                del self.instances_nrm[ready_instance.id]
            except:
                log.error("Failed to add node {}"
                          .format(ready_instance.alias), exc_info=True)
                if self.instances_nrm[ready_instance.id].handle_reboot():
                    # back to not ready list
                    self.instances.append(ready_instance)
                else:
                    # dead, delete
                    del self.instances_nrm[ready_instance.id]

    def run(self):
        """
        As soon as a new node is ready, run the add plugins commands over it.
        """
        interval = self.cluster.refresh_interval
        log.info("Waiting for one of the new nodes to be up "
                 "(updating every {}s)".format(interval))

        while any([self.unpropagated_spots, self.spots,
                   self.unpropagated_instances, self.instances]):
            ready_instances = []
            self.stream_unpropagated_spots()
            self.stream_spots()
            self.stream_unpropagated_instances()
            self.stream_update_nrm()
            self.stream_instances(ready_instances)
            self.stream_manage_reboots()
            self.stream_ready_instances(ready_instances)
            if ready_instances:
                # ready_instances means nodes were added, that took
                # time so we should loop again now
                continue
            log.info("{} Sleeping for {} seconds"
                     .format(utils.get_utc_now(), interval))
            time.sleep(interval)


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
