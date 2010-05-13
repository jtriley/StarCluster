Listing All Public StarCluster AMIs
===================================
From time to time StarCluster may provide updated AMIs. These AMIs might simply contain new OS versions or could
fix a bug experienced by StarCluster users. Either way, it's useful to be able to look at the *latest* available 
StarCluster AMIs.

To look at a list of all currently available public StarCluster AMIs, including 32bit and 64bit, run the 
**listpublic** command:

.. code-block:: none

        $ starcluster listpublic

At the time of writing this doc the output looks like;

.. code-block:: none

        $ starcluster listpublic
        StarCluster - (http://web.mit.edu/starcluster)
        Software Tools for Academics and Researchers (STAR)
        Please submit bug reports to starcluster@mit.edu

        >>> Listing all public StarCluster images...

        32bit Images:
        -------------
        [0] ami-0330d16a us-east-1 starcluster-base-ubuntu-9.04-i386-rc1
        [1] ami-8f9e71e6 us-east-1 starcluster-base-ubuntu-9.04-x86
        [2] ami-17b15e7e us-east-1 starcluster-base-ubuntu-9.10-x86-rc7

        64bit Images:
        --------------
        [0] ami-0f30d166 us-east-1 starcluster-base-ubuntu-9.04-x86_64-rc1
        [1] ami-a19e71c8 us-east-1 starcluster-base-ubuntu-9.04-x86_64
        [2] ami-2941ad40 us-east-1 starcluster-base-ubuntu-9.10-x86_64-rc3

        total images: 6
