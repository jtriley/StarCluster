#!/usr/bin/env python
config_template = """
[aws]
#replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key

# replace this with your account number
AWS_USER_ID= #your userid

[cluster mycluster]
# change this to your keypair location 
# (see the EC2 getting started guide tutorial on using ec2-add-keypair)
KEYNAME = #your keypair name
KEY_LOCATION = #/path/to/your/keypair

# cluster size
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
"""
