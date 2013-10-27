.. _users-plugin:

###################
Create Users Plugin
###################

This plugin creates one or more cluster users and configures passwordless SSH
access between cluster nodes for each user.

*************
Configuration
*************
To use the ``users`` plugin add a **[plugin]** section to your starcluster config
file:

.. code-block:: ini

    [plugin createusers]
    setup_class = starcluster.plugins.users.CreateUsers
    num_users = 30

The above config will create and configure 30 cluster users along with
passwordless SSH access on the cluster for each user. In this case usernames
are auto-generated to be user001, user002, etc. If you'd prefer to provide the
usernames instead of auto-generating them use the following config instead:

.. code-block:: ini

    [plugin createusers]
    setup_class = starcluster.plugins.users.CreateUsers
    usernames = linus, tux, larry

Next update the ``PLUGINS`` setting of one or more of your cluster templates to
include the ``createusers`` plugin:

.. code-block:: ini

    [cluster mycluster]
    plugins = createusers

The next time you start a cluster using the ``mycluster`` template the plugin
will automatically be executed and users will be created. If you need to
download the SSH keys for each cluster user in order to distribute them to
users that do not have access to your AWS account please read the next
subsection.

Downloading User SSH Keys
=========================
.. warning::

    These settings will download the SSH keys for each user to your local
    computer. Please be aware that these keys allow remote access to your
    cluster(s). Please use caution when storing and distributing these keys.

If you'd prefer the plugin to automatically archive and download the SSH keys
for each cluster user add the following to your **[plugin]** section:

.. code-block:: ini

    [plugin createusers]
    setup_class = starcluster.plugins.users.CreateUsers
    num_users = 30
    download_keys = True

By default this will create and download an archive containing all users' SSH
keys to ``$HOME/.starcluster/user_keys/<cluster>-<region>.tar.gz``. If you'd
prefer to store the archive in an alternate location specify the
``download_keys_dir`` setting:

.. code-block:: ini

    [plugin createusers]
    setup_class = starcluster.plugins.users.CreateUsers
    num_users = 30
    download_keys = True
    download_keys_dir = /path/to/keys/dir/

The above example will download the SSH keys archive to
``/path/to/keys/dir/<cluster>-<region>.tar.gz``.

*****
Usage
*****
Once the plugin has been configured it will automatically run the next time you
start a new cluster using the appropriate cluster template. If you already have
a cluster running that didn't originally have the plugin in its plugin list at
creation time you will need to manually run the plugin::

    % starcluster runplugin createusers mycluster
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Running plugin createusers
    >>> Creating 30 cluster users
    3/3 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring passwordless ssh for 30 cluster users
    50/50 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring scratch space for user(s): user001, user002,
    >>> user003, user004, user005, user006, user007, user008,
    >>> user009, user010, user011, user012, user013, user014,
    >>> user015, user016, user017, user018, user019, user020,
    >>> user021, user022, user023, user024, user025, user026,
    >>> user027, user028, user029, user030
    3/3 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%

After the plugin has finished executing you can easily login to the cluster as
any one of these users on any node in the cluster::

    % starcluster sshmaster -u user007 mycluster
    % starcluster sshnode -u user007 mycluster node007

Using the SSH Keys Archive
==========================
.. warning::

    Please use caution when storing and distributing these keys - they allow
    remote access to your cluster.

If you specified ``download_keys = True`` in your config then the plugin will
create and download a gzipped tar archive containing the RSA SSH keys for each
user to your local computer::

    >>> Tarring all SSH keys for cluster users...
    >>> Copying cluster users SSH keys to: mycluster-us-east-1.tar.gz
    mycluster-us-east-1.tar.gz 100% ||||||||||||||||||| Time: 00:00:00 963.07 K/s

If you did not specify ``download_keys_dir`` in your config then the tar
archive will be saved to ``$HOME/.starcluster/user_keys/<cluster>-<region>.tar.gz``
by default. The archive contains all of the RSA SSH keys for each cluster user
it created::

    % cd $HOME/.starcluster/user_keys
    % tar -tf mycluster-us-east-1.tar.gz
    ./user001.rsa
    ./user002.rsa
    ./user003.rsa
    ./user004.rsa
    ./user005.rsa
    ./user006.rsa
    ./user007.rsa
    ./user008.rsa
    ./user009.rsa
    ./user010.rsa
    ./user011.rsa
    ./user012.rsa
    ./user013.rsa
    ./user014.rsa
    ./user015.rsa
    ...

These keys can be distributed to non-AWS users to allow remote cluster access
*without AWS credentials*. You will also need to pick a cluster node for users
to login to and then distribute that node's public DNS name to your non-AWS
users. You can use the **listclusters** command to list the public DNS names
of all nodes in your cluster::

    $ starcluster listclusters mycluster
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    ---------------------------------------------------
    mycluster (security group: @sc-mycluster)
    ---------------------------------------------------
    Launch time: 2010-02-19T20:55:20.000Z
    Uptime: 00:29:42
    Zone: us-east-1c
    Keypair: mykeypair
    Cluster nodes:
         master running i-99999999 ec2-123-123-123-121.compute-1.amazonaws.com
        node001 running i-88888888 ec2-123-123-123-122.compute-1.amazonaws.com
    Total nodes: 2

As an example, let's choose the ``master`` node in the above output to be the
'login' node. Now suppose we distribute user007's username and SSH key to a
non-AWS user and also give them the public DNS name of the login node. In this
case the non-AWS user can connect to the cluster's master node as user007
using::

    % ssh -i /path/to/user007.rsa user007@ec2-123-123-123-121.compute-1.amazonaws.com
