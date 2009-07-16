#!/usr/bin/env python
config_template = """
[section aws]

#replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key

# replace this with your account number
AWS_USER_ID= #your userid

[section ssh]

# change this to your keypair location 
# (see the EC2 getting started guide tutorial on using ec2-add-keypair)
KEYNAME = #your keypair name
KEY_LOCATION = #/path/to/your/keypair

[section cluster]

# cluster size
DEFAULT_CLUSTER_SIZE = 2

# create the following user on the cluster
CLUSTER_USER = sgeadmin

# AMI for master node. Defaults to NODE_IMAGE_ID if not specified
# The base i386 StarCluster AMI is ami-efbd5c86
# The base x86_64 StarCluster AMI is ami-17bd5c7e
MASTER_IMAGE_ID = ami-efbd5c86

# AMI for worker nodes. Also used for the master node if MASTER_IMAGE_ID is not specified
# The base i386 StarCluster AMI is ami-efbd5c86
# The base x86_64 StarCluster AMI is ami-17bd5c7e
NODE_IMAGE_ID = ami-efbd5c86

# instance type
INSTANCE_TYPE = m1.small

# availability zone
AVAILABILITY_ZONE = us-east-1c

[section ebs]
# NOTE: this section is optional, uncomment to use
# attach volume to /home on master node 

#ATTACH_VOLUME = vol-abcdefgh
#VOLUME_DEVICE = /dev/sdd
#VOLUME_PARTITION = /dev/sdd1
"""
