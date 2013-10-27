#####################################
Listing the Official StarCluster AMIs
#####################################
From time to time new StarCluster AMIs may become available. These AMIs might
simply contain new OS versions or could fix a bug experienced by StarCluster
users. In any case it's useful to look at the *latest* available StarCluster
AMIs.

To look at a list of all currently available public StarCluster AMIs run the
``listpublic`` command::

    $ starcluster listpublic

This will show all available AMIs in the current region. Unless you've
specified a region in your config the default region is `us-east-1`. To view
AMIs in other regions either specify a region in your ``[aws info]`` config or
use the global ``-r`` option::

    $ starcluster -r eu-west-1 listpublic

At the time of writing this document the output for `us-east-1` looks like::

    $ starcluster listpublic
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Listing all public StarCluster images...

    32bit Images:
    -------------
    [0] ami-8cf913e5 us-east-1 starcluster-base-ubuntu-10.04-x86-rc3
    [1] ami-d1c42db8 us-east-1 starcluster-base-ubuntu-9.10-x86-rc8
    [2] ami-17b15e7e us-east-1 starcluster-base-ubuntu-9.10-x86-rc7
    [3] ami-8f9e71e6 us-east-1 starcluster-base-ubuntu-9.04-x86

    64bit Images:
    --------------
    [0] ami-0af31963 us-east-1 starcluster-base-ubuntu-10.04-x86_64-rc1
    [1] ami-8852a0e1 us-east-1 starcluster-base-ubuntu-10.04-x86_64-hadoop
    [2] ami-a5c42dcc us-east-1 starcluster-base-ubuntu-9.10-x86_64-rc4
    [3] ami-2941ad40 us-east-1 starcluster-base-ubuntu-9.10-x86_64-rc3
    [4] ami-a19e71c8 us-east-1 starcluster-base-ubuntu-9.04-x86_64
    [5] ami-06a75a6f us-east-1 starcluster-base-centos-5.4-x86_64-ebs-hvm-gpu-hadoop-rc2 (HVM-EBS)
    [6] ami-12b6477b us-east-1 starcluster-base-centos-5.4-x86_64-ebs-hvm-gpu-rc2 (HVM-EBS)

    total images: 11
