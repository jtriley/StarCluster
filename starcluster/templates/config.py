from starcluster import static

config_template = """\
####################################
## StarCluster Configuration File ##
####################################

[global]
# configure the default cluster template to use when starting a cluster
# defaults to 'smallcluster' defined below. this template should be usable
# out-of-the-box provided you've configured your keypair correctly
DEFAULT_TEMPLATE=smallcluster
# enable experimental features for this release
ENABLE_EXPERIMENTAL=False
# number of seconds to wait when polling instances (default: 30s)
#REFRESH_INTERVAL=15
# specify a web browser to launch when viewing spot history plots
#WEB_BROWSER=chromium

[aws info]
# This is the AWS credentials section.
# These settings apply to all clusters
# replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key
# replace this with your account number
AWS_USER_ID= #your userid
# Uncomment to specify a different Amazon AWS region  (OPTIONAL)
# (defaults to us-east-1 if not specified)
# NOTE: AMIs have to be migrated!
#AWS_REGION_NAME = eu-west-1
#AWS_REGION_HOST = ec2.eu-west-1.amazonaws.com
# Uncomment these settings when creating an instance-store (S3) AMI (OPTIONAL)
#EC2_CERT = /path/to/your/cert-asdf0as9df092039asdfi02089.pem
#EC2_PRIVATE_KEY = /path/to/your/pk-asdfasd890f200909.pem
# Uncomment these settings to use a proxy host when connecting to AWS
#aws_proxy = your.proxyhost.com
#aws_proxy_port = 8080
#aws_proxy_user = yourproxyuser
#aws_proxy_pass = yourproxypass

# Sections starting with "key" define your keypairs
# (see the EC2 getting started guide tutorial on using ec2-add-keypair to learn
# how to create new keypairs)
# Section name should match your key name e.g.:
[key gsg-keypair]
KEY_LOCATION=/home/myuser/.ssh/id_rsa-gsg-keypair

# You can of course have multiple keypair sections
# [key my-other-gsg-keypair]
# KEY_LOCATION=/home/myuser/.ssh/id_rsa-my-other-gsg-keypair

# Sections starting with "cluster" define your cluster templates
# Section name is the name you give to your cluster template e.g.:
[cluster smallcluster]
# change this to the name of one of the keypair sections defined above
KEYNAME = gsg-keypair

# number of ec2 instances to launch
CLUSTER_SIZE = 2

# create the following user on the cluster
CLUSTER_USER = sgeadmin

# optionally specify shell (defaults to bash)
# (options: %(shells)s)
CLUSTER_SHELL = bash

# AMI to use for cluster nodes. These AMIs are for the us-east-1 region.
# Use the 'listpublic' command to list StarCluster AMIs in other regions
# The base i386 StarCluster AMI is %(x86_ami)s
# The base x86_64 StarCluster AMI is %(x86_64_ami)s
# The base HVM StarCluster AMI is %(hvm_ami)s
NODE_IMAGE_ID = %(x86_ami)s
# instance type for all cluster nodes
# (options: %(instance_types)s)
NODE_INSTANCE_TYPE = m1.small

# Uncomment to disable installing/configuring a queueing system on the
# cluster (SGE)
#DISABLE_QUEUE=True

# Uncomment to specify a different instance type for the master node (OPTIONAL)
# (defaults to NODE_INSTANCE_TYPE if not specified)
#MASTER_INSTANCE_TYPE = m1.small

# Uncomment to specify a separate AMI to use for the master node. (OPTIONAL)
# (defaults to NODE_IMAGE_ID if not specified)
#MASTER_IMAGE_ID = %(x86_ami)s (OPTIONAL)

# availability zone to launch the cluster in (OPTIONAL)
# (automatically determined based on volumes (if any) or
# selected by Amazon if not specified)
#AVAILABILITY_ZONE = us-east-1c

# list of volumes to attach to the master node (OPTIONAL)
# these volumes, if any, will be NFS shared to the worker nodes
# see "Configuring EBS Volumes" below on how to define volume sections
#VOLUMES = oceandata, biodata

# list of plugins to load after StarCluster's default setup routines (OPTIONAL)
# see "Configuring StarCluster Plugins" below on how to define plugin sections
#PLUGINS = myplugin, myplugin2

# list of permissions (or firewall rules) to apply to the cluster's security
# group (OPTIONAL).
#PERMISSIONS = ssh, http

# Uncomment to always create a spot cluster when creating a new cluster from
# this template. The following example will place a $0.50 bid for each spot
# request.
#SPOT_BID = 0.50

###########################################
## Defining Additional Cluster Templates ##
###########################################

# You can also define multiple cluster templates.
# You can either supply all configuration options as with smallcluster above,
# or create an EXTENDS=<cluster_name> variable in the new cluster section to
# use all settings from <cluster_name> as defaults. Below are a couple of
# example cluster templates that use the EXTENDS feature:

# [cluster mediumcluster]
# Declares that this cluster uses smallcluster as defaults
# EXTENDS=smallcluster
# This section is the same as smallcluster except for the following settings:
# KEYNAME=my-other-gsg-keypair
# NODE_INSTANCE_TYPE = c1.xlarge
# CLUSTER_SIZE=8
# VOLUMES = biodata2

# [cluster largecluster]
# Declares that this cluster uses mediumcluster as defaults
# EXTENDS=mediumcluster
# This section is the same as mediumcluster except for the following variables:
# CLUSTER_SIZE=16

#############################
## Configuring EBS Volumes ##
#############################

# A new [volume] section must be created for each EBS volume you wish to use
# with StarCluser. The section name is a tag for your volume. This tag is used
# in the VOLUMES setting of a cluster template to declare that an EBS volume is
# to be mounted and nfs shared on the cluster. (see the commented VOLUMES
# setting in the example 'smallcluster' template above)
# Below are some examples of defining and configuring EBS volumes to be used
# with StarCluster:

# Sections starting with "volume" define your EBS volumes
# Section name tags your volume e.g.:
# [volume biodata]
# (attach 1st partition of volume vol-c9999999 to /home on master node)
# VOLUME_ID = vol-c999999
# MOUNT_PATH = /home

# Same volume as above, but mounts to different location
# [volume biodata2]
# (attach 1st partition of volume vol-c9999999 to /opt/ on master node)
# VOLUME_ID = vol-c999999
# MOUNT_PATH = /opt/

# Another volume example
# [volume oceandata]
# (attach 1st partition of volume vol-d7777777 to /mydata on master node)
# VOLUME_ID = vol-d7777777
# MOUNT_PATH = /mydata

# Same as oceandata only uses the 2nd partition instead
# [volume oceandata]
# (attach 2nd partition of volume vol-d7777777 to /mydata on master node)
# VOLUME_ID = vol-d7777777
# MOUNT_PATH = /mydata
# PARTITION = 2

#####################################
## Configuring StarCluster Plugins ##
#####################################

# Sections starting with "plugin" define a custom python class which can
# perform additional configurations to StarCluster's default routines. These
# plugins can be assigned to a cluster template to customize the setup
# procedure when starting a cluster from this template
# (see the commented PLUGINS setting in the 'smallcluster' template above)
# Below is an example of defining a plugin called 'myplugin':

# [plugin myplugin]
# myplugin module either lives in ~/.starcluster/plugins or is
# in your PYTHONPATH
# SETUP_CLASS = myplugin.SetupClass
# extra settings are passed as arguments to your plugin:
# SOME_PARAM_FOR_MY_PLUGIN = 1
# SOME_OTHER_PARAM = 2

############################################
## Configuring Security Group Permissions ##
############################################

# [permission ssh]
# protocol can be: tcp, udp, or icmp
# protocol = tcp
# from_port = 22
# to_port = 22
# cidr_ip = <your_ip>/32

# example for opening port 80 on the cluster to a specific IP range
# [permission http]
# protocol = tcp
# from_port = 80
# to_port = 80
# cidr_ip = 18.0.0.0/24
""" % {
    'x86_ami': static.BASE_AMI_32,
    'x86_64_ami': static.BASE_AMI_64,
    'hvm_ami': static.BASE_AMI_HVM,
    'instance_types': ', '.join(static.INSTANCE_TYPES.keys()),
    'shells': ', '.join(static.AVAILABLE_SHELLS.keys()),
}

DASHES = '-' * 10
copy_below = ' '.join([DASHES, 'COPY BELOW THIS LINE', DASHES])
end_copy = ' '.join([DASHES, 'END COPY', DASHES])
copy_paste_template = '\n'.join([copy_below, config_template, end_copy]) + '\n'
