Listing All Public StarCluster AMIs
===================================
From time to time StarCluster may provide updated AMIs. These AMIs might simply
contain new OS versions or could fix a bug experienced by StarCluster users.
Either way, it's useful to be able to look at the *latest* available
StarCluster AMIs.

To look at a list of all currently available public StarCluster AMIs, including
32bit and 64bit, run the **listpublic** command::

    $ starcluster listpublic

At the time of writing this doc the output looks like::

    $ starcluster listpublic
    StarCluster - (http://web.mit.edu/starcluster) (v. 0.9999)
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
