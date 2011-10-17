MySQL Cluster Plugin
====================
This plugin automates the configuration and startup of MySQL Cluster on Ubuntu
10.04 Lucid Lynx. The mysql-cluster-server package suffers from an
`installation bug`_ as of 7/21/10. This plugin works its way around that bug
and results in an operational MySQL Cluster on initialization of the cluster.

Configuration Options
---------------------
Here is an example of the mysqlcluster plugin section of the StarCluster config
file:

.. code-block:: ini

    [plugin mysqlcluster]
    SETUP_CLASS = mysqlcluster.MysqlCluster
    NUM_REPLICAS = 2
    DATA_MEMORY = 80M
    INDEX_MEMORY = 18M
    DATA_DIR = /var/lib/mysqlcluster
    BACKUP_DATA_DIR = /var/lib/mysqlcluster/
    DEDICATED_QUERY = True
    NUM_DATA_NODES = 2

**NUM_REPLICAS**: Specifies number of replicas for each table in the cluster,
as well as the number of node groups. The maximum value is 4, and only values 1
and 2 are currently supported by MySQL. A value of 1 would indicate that that
there is only one copy of your data. The loss of a single data note would
therefore cause your cluster to fail, as there are no additional copies of that
data. The number of replicas must also divide evenly into the number of data
nodes. '2' is both the recommended and default setting for this parameter.

**DATA_MEMORY**: Amount of space (in bytes) available for storing database
records.  Suffixes K, M, and G can be used to indicated Kilobytes, Megabytes,
or Gigabytes. Default value is 80M, minimum is 1M.

**INDEX_MEMORY**: Amount of storage used for hash indexes in the MySQL Cluster.
Default value is 18M, minimum is 1M.

**DATA_DIR**: Specifies the directory where metadata, REDO logs, UNDO logs (for
Disk Data tables), data files, trace files, log files, pid files and error logs
are placed.

**BACKUP_DATA_DIR**: Specifies the directory in which to put the BACKUP
directory. Defaults to DATA_DIR.

**DEDICATED_QUERY**: True indicates that the data nodes do not also function as
query nodes, and there are instead dedicated nodes to accept queries. False
indicates that all data nodes will also accept queries.

**NUM_DATA_NODES**: Number of data nodes if DEDICATED_QUERY is set to True. The
remaining nodes in the cluster will be MySQL query nodes.

What This Plugin Does
---------------------
#. Creates data and backup directories, changes ownership to mysql user
#. Generates /etc/mysql/ndb_mgmd.cnf configuration file on master.
#. Generates /etc/mysql/my.cnf configuration file on all nodes.
#. Kills mysql processes on all nodes.
#. Starts Management Client on master.
#. Starts mysql on query nodes
#. Starts mysql-ndb on data nodes.

Creating a Replicated Table
---------------------------
Here is an example of how to create a table that is replicated across
the cluster. Do this on one of the data nodes:

.. code-block:: mysql

    mysql> create database testdb;
    Query OK, 1 row affected (0.00 sec)
    mysql> use testcluster;
    Database changed
    mysql> create table testtable (i int) engine=ndbcluster;
    Query OK, 0 rows affected (0.71 sec)
    mysql> insert into testtable values (1);
    Query OK, 1 row affected (0.05 sec)
    mysql> select * from testtable;
    +------+
    | i    |
    +------+
    |    1 |
    +------+
    1 row in set (0.03 sec)

Note that 'engine=ndbcluster' is what indicates that the table should be
created in a cluster configuration. If it is not used, the table will not be
replicated.

On another data node:

.. code-block:: mysql

    mysql> use testdb;
    Database changed
    mysql> select * from testtable;
    +------+
    | i    |
    +------+
    |    1 |
    +------+
    1 row in set (0.04 sec)

The table has been replicated, and the cluster is working.

Recommendations for Use
-----------------------
* Clusters should have three nodes at the very least.
* NUM_REPLICAS should probably stay at 2. Consequently, there should be an even
  number of data nodes.
* Set DATA_DIR and BACKUP_DATA_DIR to an EBS volume if you want the data to
  persist.

.. _installation bug: https://bugs.launchpad.net/ubuntu/+source/mysql-cluster-7.0/+bug/579732
