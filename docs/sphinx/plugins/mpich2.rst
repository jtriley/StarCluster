.. _mpich2-plugin:

#############
MPICH2 Plugin
#############

By default StarCluster includes OpenMPI. However, for either performance or
compatibility reasons, you may wish to use MPICH2 which provides an alternate
MPI implementation. The ``MPICH2`` plugin will install and configure MPICH2 on
your clusters.

*****
Usage
*****
To use this plugin add a plugin section to your starcluster config file:

.. code-block:: ini

    [plugin mpich2]
    setup_class = starcluster.plugins.mpich2.MPICH2Setup

Next update the ``PLUGINS`` setting of one or more of your cluster templates to
include the ``MPICH2`` plugin:

.. code-block:: ini

    [cluster mycluster]
    plugins = mpich2

The next time you start a cluster the ``MPICH2`` plugin will automatically be
executed and ``MPICH2`` will be installed and configured on all nodes. If you
already have a cluster running that didn't originally have ``MPICH2`` in its
plugin list you can manually run the plugin using::

    $ starcluster runplugin mpich2 mycluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Running plugin mpich2
    >>> Setting up MPICH2 hosts file on all nodes
    3/3 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Setting MPICH2 as default MPI on all nodes
    3/3 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> MPICH2 is now ready to use
    >>> Use mpicc, mpif90, mpirun, etc. to compile and run your MPI apps

*********************************
Building and Running MPI Programs
*********************************
To build your MPI code use the standard procedure of compiling with ``mpicc``,
``mpic++``, or ``mpif90``::

    $ starcluster sshmaster mycluster -u myuser
    myuser@master $ cat << EOF > mpihelloworld.c
    /* C Example */
    #include <stdio.h>
    #include <mpi.h>
    #include <unistd.h>
    int main (argc, argv)
         int argc;
         char *argv[];
    {
      char hostname[1024];
      gethostname(hostname, 1024);
      int rank, size;
      MPI_Init (&argc, &argv);      /* starts MPI */
      MPI_Comm_rank (MPI_COMM_WORLD, &rank);        /* get current process id */
      MPI_Comm_size (MPI_COMM_WORLD, &size);        /* get number of processes */
      printf("Hello world from process %d of %d on %s\n", rank, size, hostname);
      MPI_Finalize();
      return 0;
    }
    EOF
    myuser@master $ mpicc -o mpihw mpihelloworld.c

.. note::

    You should put the MPI binary in your $HOME folder on the cluster in order
    for the binary to be NFS-shared to the rest of the nodes in the cluster.

To run the code simply use ``mpirun`` and pass in the number of processors you
wish to use on the cluster via the ``-np`` option::

    myuser@master $ mpirun -np 3 ./mpihw
    Hello world from process 0 of 3 on master
    Hello world from process 2 of 3 on node002
    Hello world from process 1 of 3 on node001

This will use 3 processors to run the hello world MPI code above. You do not
need to create or specify a hosts file. The hostfile is automatically created
and set as the default ``MPICH2`` hosts file by the plugin.
