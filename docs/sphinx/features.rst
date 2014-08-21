Features
========

* Simple configuration with sensible defaults
* Single "start" command to automatically launch and configure one or more
  clusters on EC2
* Support for attaching and NFS-sharing Amazon Elastic Block Storage (EBS)
  volumes for persistent storage across a cluster
* Comes with publicly available Ubuntu-based Amazon Machine Images (AMI)
  configured for distributed and parallel computing.
* AMI includes OpenMPI, OpenBLAS, Lapack, NumPy, SciPy, and other useful
  scientific libraries.
* Clusters are automatically configured with NFS, Open Grid Scheduler (formerly
  SGE) queuing system, and password-less ssh between machines
* Plugin System - plugin framework that enables users to customize the cluster.
  Plugins are executed when adding/removing a node as well as when
  restarting/shutting down the entire cluster. StarCluster has many
  :ref:`built-in plugins<plugins-index>` ready to use out-of-the-box. Users
  can also implement their own plugins to further customize the cluster for
  their needs.
* EBS-Backed Clusters - Support for starting/stopping EBS-backed clusters on
  EC2.
* Cluster Compute Instances - Support for all cluster compute instance types.
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
  workload.
* Security Group Permissions - ability to specify permission settings to be
  applied automatically to a cluster's security group after it's been started.
* Multiple Instance Types - support for specifying instance types on a per-node
  basis.
* Unpartitioned Volumes - StarCluster supports both partitioned and
  unpartitioned EBS volumes.
* Numerous helper commands for common EC2/S3 operations::

      listinstances: List all running EC2 instances
      listspots: List all EC2 spot instance requests
      listimages: List all registered EC2 images (AMIs)
      listpublic: List all public StarCluster images on EC2
      listkeypairs: List all EC2 keypairs
      createkey: Create a new Amazon EC2 keypair
      removekey: Remove a keypair from Amazon EC2
      s3image: Create a new instance-store (S3) AMI from a running EC2 instance
      ebsimage: Create a new EBS image (AMI) from a running EC2 instance
      showimage: Show all AMI parts and manifest files on S3 for an instance-store AMI
      downloadimage: Download the manifest.xml and all AMI parts for an instance-store AMI
      removeimage: Deregister an EC2 image (AMI)
      createvolume: Create a new EBS volume for use with StarCluster
      listvolumes: List all EBS volumes
      resizevolume: Resize an existing EBS volume
      removevolume: Delete one or more EBS volumes
      spothistory: Show spot instance pricing history stats (last 30 days by default)
      showconsole: Show console output for an EC2 instance
      listregions: List all EC2 regions
      listzones: List all EC2 availability zones in the current region (default: us-east-1)
      listbuckets: List all S3 buckets
      showbucket: Show all files in an S3 bucket
