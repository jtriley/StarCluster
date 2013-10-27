# Copyright 2009-2013 Justin Riley
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

from starcluster import static

config_template = """\
####################################
## StarCluster Configuration File ##
####################################
[global]
# Configure the default cluster template to use when starting a cluster
# defaults to 'smallcluster' defined below. This template should be usable
# out-of-the-box provided you've configured your keypair correctly
DEFAULT_TEMPLATE=smallcluster
# enable experimental features for this release
#ENABLE_EXPERIMENTAL=True
# number of seconds to wait when polling instances (default: 30s)
#REFRESH_INTERVAL=15
# specify a web browser to launch when viewing spot history plots
#WEB_BROWSER=chromium
# split the config into multiple files
#INCLUDE=~/.starcluster/aws, ~/.starcluster/keys, ~/.starcluster/vols

#############################################
## AWS Credentials and Connection Settings ##
#############################################
[aws info]
# This is the AWS credentials section (required).
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
#AWS_PROXY = your.proxyhost.com
#AWS_PROXY_PORT = 8080
#AWS_PROXY_USER = yourproxyuser
#AWS_PROXY_PASS = yourproxypass

###########################
## Defining EC2 Keypairs ##
###########################
# Sections starting with "key" define your keypairs. See "starcluster createkey
# --help" for instructions on how to create a new keypair. Section name should
# match your key name e.g.:
[key mykey]
KEY_LOCATION=~/.ssh/mykey.rsa

# You can of course have multiple keypair sections
# [key myotherkey]
# KEY_LOCATION=~/.ssh/myotherkey.rsa

################################
## Defining Cluster Templates ##
################################
# Sections starting with "cluster" represent a cluster template. These
# "templates" are a collection of settings that define a single cluster
# configuration and are used when creating and configuring a cluster. You can
# change which template to use when creating your cluster using the -c option
# to the start command:
#
#     $ starcluster start -c mediumcluster mycluster
#
# If a template is not specified then the template defined by DEFAULT_TEMPLATE
# in the [global] section above is used. Below is the "default" template named
# "smallcluster". You can rename it but dont forget to update the
# DEFAULT_TEMPLATE setting in the [global] section above. See the next section
# on defining multiple templates.

[cluster smallcluster]
# change this to the name of one of the keypair sections defined above
KEYNAME = mykey
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
# Uncomment to specify one or more userdata scripts to use when launching
# cluster instances. Supports cloudinit. All scripts combined must be less than
# 16KB
#USERDATA_SCRIPTS = /path/to/script1, /path/to/script2

###########################################
## Defining Additional Cluster Templates ##
###########################################
# You can also define multiple cluster templates. You can either supply all
# configuration options as with smallcluster above, or create an
# EXTENDS=<cluster_name> variable in the new cluster section to use all
# settings from <cluster_name> as defaults. Below are example templates that
# use the EXTENDS feature:

# [cluster mediumcluster]
# Declares that this cluster uses smallcluster as defaults
# EXTENDS=smallcluster
# This section is the same as smallcluster except for the following settings:
# KEYNAME=myotherkey
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
# StarCluster can attach one or more EBS volumes to the master and then
# NFS_share these volumes to all of the worker nodes. A new [volume] section
# must be created for each EBS volume you wish to use with StarCluser. The
# section name is a tag for your volume. This tag is used in the VOLUMES
# setting of a cluster template to declare that an EBS volume is to be mounted
# and nfs shared on the cluster. (see the commented VOLUMES setting in the
# example 'smallcluster' template above) Below are some examples of defining
# and configuring EBS volumes to be used with StarCluster:

# Sections starting with "volume" define your EBS volumes
# [volume biodata]
# attach vol-c9999999 to /home on master node and NFS-shre to worker nodes
# VOLUME_ID = vol-c999999
# MOUNT_PATH = /home

# Same volume as above, but mounts to different location
# [volume biodata2]
# VOLUME_ID = vol-c999999
# MOUNT_PATH = /opt/

# Another volume example
# [volume oceandata]
# VOLUME_ID = vol-d7777777
# MOUNT_PATH = /mydata

# By default StarCluster will attempt first to mount the entire volume device,
# failing that it will try the first partition. If you have more than one
# partition you will need to set the PARTITION number, e.g.:
# [volume oceandata]
# VOLUME_ID = vol-d7777777
# MOUNT_PATH = /mydata
# PARTITION = 2

############################################
## Configuring Security Group Permissions ##
############################################
# Sections starting with "permission" define security group rules to
# automatically apply to newly created clusters. IP_PROTOCOL in the following
# examples can be can be: tcp, udp, or icmp. CIDR_IP defaults to 0.0.0.0/0 or
# "open to the # world"

# open port 80 on the cluster to the world
# [permission http]
# IP_PROTOCOL = tcp
# FROM_PORT = 80
# TO_PORT = 80

# open https on the cluster to the world
# [permission https]
# IP_PROTOCOL = tcp
# FROM_PORT = 443
# TO_PORT = 443

# open port 80 on the cluster to an ip range using CIDR_IP
# [permission http]
# IP_PROTOCOL = tcp
# FROM_PORT = 80
# TO_PORT = 80
# CIDR_IP = 18.0.0.0/8

# restrict ssh access to a single ip address (<your_ip>)
# [permission ssh]
# IP_PROTOCOL = tcp
# FROM_PORT = 22
# TO_PORT = 22
# CIDR_IP = <your_ip>/32


#####################################
## Configuring StarCluster Plugins ##
#####################################
# Sections starting with "plugin" define a custom python class which perform
# additional configurations to StarCluster's default routines. These plugins
# can be assigned to a cluster template to customize the setup procedure when
# starting a cluster from this template (see the commented PLUGINS setting in
# the 'smallcluster' template above). Below is an example of defining a user
# plugin called 'myplugin':

# [plugin myplugin]
# NOTE: myplugin module must either live in ~/.starcluster/plugins or be
# on your PYTHONPATH
# SETUP_CLASS = myplugin.SetupClass
# extra settings are passed as __init__ arguments to your plugin:
# SOME_PARAM_FOR_MY_PLUGIN = 1
# SOME_OTHER_PARAM = 2

######################
## Built-in Plugins ##
######################
# The following plugins ship with StarCluster and should work out-of-the-box.
# Uncomment as needed. Don't forget to update your PLUGINS list!
# See http://star.mit.edu/cluster/docs/latest/plugins for plugin details.
#
# Use this plugin to install one or more packages on all nodes
# [plugin pkginstaller]
# SETUP_CLASS = starcluster.plugins.pkginstaller.PackageInstaller
# # list of apt-get installable packages
# PACKAGES = mongodb, python-pymongo
#
# Use this plugin to create one or more cluster users and download all user ssh
# keys to $HOME/.starcluster/user_keys/<cluster>-<region>.tar.gz
# [plugin createusers]
# SETUP_CLASS = starcluster.plugins.users.CreateUsers
# NUM_USERS = 30
# # you can also comment out NUM_USERS and specify exact usernames, e.g.
# # usernames = linus, tux, larry
# DOWNLOAD_KEYS = True
#
# Use this plugin to configure the Condor queueing system
# [plugin condor]
# SETUP_CLASS = starcluster.plugins.condor.CondorPlugin
#
# The SGE plugin is enabled by default and not strictly required. Only use this
# if you want to tweak advanced settings in which case you should also set
# DISABLE_QUEUE=TRUE in your cluster template. See the plugin doc for more
# details.
# [plugin sge]
# SETUP_CLASS = starcluster.plugins.sge.SGEPlugin
# MASTER_IS_EXEC_HOST = False
#
# The IPCluster plugin configures a parallel IPython cluster with optional
# web notebook support. This allows you to run Python code in parallel with low
# latency message passing via ZeroMQ.
# [plugin ipcluster]
# SETUP_CLASS = starcluster.plugins.ipcluster.IPCluster
# # Enable the IPython notebook server (optional)
# ENABLE_NOTEBOOK = True
# # Set a password for the notebook for increased security
# # This is optional but *highly* recommended
# NOTEBOOK_PASSWD = a-secret-password
# # Set a custom directory for storing/loading notebooks (optional)
# NOTEBOOK_DIRECTORY = /path/to/notebook/dir
# # Set a custom packer. Must be one of 'json', 'pickle', or 'msgpack'
# # This is optional.
# PACKER = pickle
#
# Use this plugin to create a cluster SSH "dashboard" using tmux. The plugin
# creates a tmux session on the master node that automatically connects to all
# the worker nodes over SSH. Attaching to the session shows a separate window
# for each node and each window is logged into the node via SSH.
# [plugin tmux]
# SETUP_CLASS = starcluster.plugins.tmux.TmuxControlCenter
#
# Use this plugin to change the default MPI implementation on the
# cluster from OpenMPI to MPICH2.
# [plugin mpich2]
# SETUP_CLASS = starcluster.plugins.mpich2.MPICH2Setup
#
# Configure a hadoop cluster. (includes dumbo setup)
# [plugin hadoop]
# SETUP_CLASS = starcluster.plugins.hadoop.Hadoop
#
# Configure a distributed MySQL Cluster
# [plugin mysqlcluster]
# SETUP_CLASS = starcluster.plugins.mysql.MysqlCluster
# NUM_REPLICAS = 2
# DATA_MEMORY = 80M
# INDEX_MEMORY = 18M
# DUMP_FILE = test.sql
# DUMP_INTERVAL = 60
# DEDICATED_QUERY = True
# NUM_DATA_NODES = 2
#
# Install and setup an Xvfb server on each cluster node
# [plugin xvfb]
# SETUP_CLASS = starcluster.plugins.xvfb.XvfbSetup
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
