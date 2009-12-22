#!/usr/bin/env python
config_template = """
# This is the global AWS section.
# These settings apply to all clusters
[aws]
#replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key
# replace this with your account number
AWS_USER_ID= #your userid

# Sections starting with "key" define your keypairs
# Section name should match your key name e.g.:
[key gsg-keypair]
KEY_LOCATION=/home/myuser/.ssh/id_rsa-gsg-keypair

# You can of course have multiple keypair sections
[key my-other-gsg-keypair]
KEY_LOCATION=/home/myuser/.ssh/id_rsa-my-other-gsg-keypair

# Sections starting with "cluster" define your cluster configurations
# Section name is the name you give to your cluster e.g.:
[cluster smallcluster]
# change this to the name of one of the keypair sections defined above 
# (see the EC2 getting started guide tutorial on using ec2-add-keypair to learn
# how to create new keypairs)
KEYNAME = gsg-keypair

# number of ec2 instances to launch
CLUSTER_SIZE = 2

# create the following user on the cluster
CLUSTER_USER = sgeadmin
# optionally specify shell (defaults to bash)
# options: bash, zsh, csh, ksh, tcsh
CLUSTER_SHELL = bash

# AMI for master node. Defaults to NODE_IMAGE_ID if not specified
# The base i386 StarCluster AMI is ami-0330d16a
# The base x86_64 StarCluster AMI is ami-0f30d166
MASTER_IMAGE_ID = ami-0330d16a

# AMI for worker nodes. Also used for the master node if MASTER_IMAGE_ID is not specified
# The base i386 StarCluster AMI is ami-0330d16a
# The base x86_64 StarCluster AMI is ami-0f30d166
NODE_IMAGE_ID = ami-0330d16a

# instance type
INSTANCE_TYPE = m1.small

# availability zone
AVAILABILITY_ZONE = us-east-1c

# attach volume to /home on master node 
# NOTE: these settings are optional, uncomment to use them
#ATTACH_VOLUME = vol-abcdefgh
#VOLUME_DEVICE = /dev/sdd
#VOLUME_PARTITION = /dev/sdd1

# You can also define multiple clusters.
# You can either supply all configuration options as with smallcluster above, or
# create an EXTENDS=<cluster name> variable in the new cluster section to use all 
# settings from another cluster section e.g.:
[cluster mediumcluster]
EXTENDS=smallcluster
KEYNAME=my-other-gsg-keypair
INSTANCE_TYPE = c1.xlarge
CLUSTER_SIZE=8

[cluster largecluster]
EXTENDS=mediumcluster
CLUSTER_SIZE=16
"""
