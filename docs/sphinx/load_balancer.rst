*********************************
StarCluster Elastic Load Balancer
*********************************
This load balancer grows and shrinks a Sun Grid Engine cluster according to the
length of the cluster's job queue. When the cluster is heavily loaded and 
processing a long job queue, ELB can gradually add more nodes, up to the 
specified max_nodes, to distribute the work and improve throughput. When the queue
becomes empty, ELB can remove idle nodes in order to save money. The cluster
will shrink down to one node (the master), terminating all of the other nodes
as they become idle.

Usage
-----
To use the Elastic Load Balancer, you can start it from the command line:

.. code-block:: none

    starcluster loadbalance cluster_tag

    or

    starcluster bal cluster_tag

This will start the load balancer in an infinite loop. It can be terminated by 
pressing CTRL-C.


Configuration
-------------
At this time, all of the parameters are stored in the file 
starcluster/balancer/sge/__init__.py
with the appropriate descriptions. Before release, those configuration options
will be moved to the standard starcluster configuration file.


Capabilities
------------
There is a polling loop, default is 60 seconds, set in the configuration of the
load balancer. Every 60 seconds, the load balancer will connect to the cluster,
obtain statistics from Sun Grid Engine, and decide what to do about the
job queue. ELB deals only with the queue length and active machines. ELB does
not examine the load on any of the hosts. If we had the ability to migrate jobs
from an overloaded host to an idle host, then we would spend more time looking 
at individual hosts' system load. However, since job migration is out of the scope
of this project and starcluster in general, we do not look at system load.

This diagram illustrates the decisions that ELB will make in each loop:

.. image:: http://dl.dropbox.com/u/224960/starcluster-decision-diagram.jpg

TODO: Move this image to a permanent location on web.mit.edu


