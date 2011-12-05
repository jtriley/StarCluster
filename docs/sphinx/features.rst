Features
========

  * Simple configuration with sensible defaults
  * Single "start" command to automatically launch and configure one or more
    clusters on EC2
  * Support for attaching and NFS-sharing Amazon Elastic Block Storage (EBS)
    volumes for persistent storage across a cluster
  * Comes with a publicly available Amazon Machine Image (AMI) configured for
    scientific computing
  * AMI includes OpenMPI, ATLAS, Lapack, NumPy, SciPy, and other useful
    libraries
  * Clusters are automatically configured with NFS, Sun Grid Engine queuing
    system, and password-less ssh between machines
  * Supports user-contributed "plugins" that allow users to perform additional
    setup routines on the cluster after StarCluster's defaults
  * EBS-Backed Clusters - Added support for starting/stopping EBS-backed
    clusters on EC2.
  * Cluster Compute Instances - Added support for the new Cluster Compute
    instance type. Thanks to Fred Rotbart for his contributions.
  * Ability to Add/Remove Nodes- Added new addnode and removenode commands for
    adding/removing nodes to a cluster and removing existing nodes from a
    cluster.
  * Restart command - Added new restart command that reboots the cluster and
    reconfigures the cluster.
  * Create Keypairs - Added ability to add/list/remove keypairs
  * Elastic Load Balancing - Support for shrinking/expanding clusters based on
    Sun Grid Engine queue statistics. This allow the user to start a
    single-node cluster (or larger) and scale the number of instances needed to
    meet the current queue load. For example, a single-node cluster can be
    launched and as the queue load increases new EC2 instances are launched,
    added to the cluster, used for computation, and then removed when they're
    idle. This minimizes the cost of using EC2 for an unknown and on-demand
    workload. This feature is now available in the latest github code thanks to
    Rajat Banerjee (rqbanerjee).
  * Security Group Permissions - Added ability to specify permission settings
    to be applied automatically to a cluster's security group after it's been
    started.
  * Multiple Instance Types - Added support for specifying instance types on a
    per-node basis. Thanks to Dan Yamins for his contributions.
  * Unpartitioned Volumes - StarCluster now supports both partitioned and
    unpartitioned EBS volumes.
  * New Plugin Hooks - Plugins can now play a part when adding/removing a node
    as well as when restarting/shutting down the entire cluster by implementing
    the on_remove_node/on_add_node/on_shutdown/on_reboot methods
