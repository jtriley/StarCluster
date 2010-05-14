#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'StarCluster',
    version = '0.91',
    packages = ['starcluster', 'starcluster.templates', 'starcluster.tests', 'starcluster.tests.templates'],
    package_dir = {'starcluster':'starcluster'},
    scripts=['bin/starcluster',],

    install_requires=[
        "paramiko>=1.7.6",
        "boto>=1.9b",
    ],

    zip_safe = True,

    author='Justin Riley',
    author_email='justin.t.riley@gmail.com',
    url="http://web.mit.edu/starcluster",
    description="StarCluster is a utility for creating and managing computing clusters hosted on Amazon's Elastic Compute Cloud (EC2).",
    long_description = """
    StarCluster is a utility for creating and managing computing clusters hosted on 
    Amazon's Elastic Compute Cloud (EC2). StarCluster utilizes Amazon's EC2 web service 
    to create and destroy clusters of Linux virtual machines on demand.

    To get started, the user creates a simple configuration file with their AWS account 
    details and a few cluster preferences (e.g. number of machines, machine type, ssh 
    keypairs, etc). After creating the configuration file and running StarCluster's 
    "start" command, a cluster of Linux machines configured with the Sun Grid Engine 
    queuing system, an NFS-shared /home directory, and OpenMPI with password-less ssh is 
    created and ready to go out-of-the-box. Running StarCluster's "stop" command will 
    shutdown the cluster and stop paying for service. This allows the user to only pay 
    for what they use.

    StarCluster can also utilize Amazon's Elastic Block Storage (EBS) volumes to provide 
    persistent data storage for a cluster. EBS volumes allow you to store large amounts 
    of data in the Amazon cloud and are also easy to back-up and replicate in the cloud. 
    StarCluster will mount and NFS-share any volumes specified in the config. StarCluster's 
    "createvolume" command provides the ability to automatically create, format, and 
    partition new EBS volumes for use with StarCluster.

    StarCluster provides a Ubuntu-based Amazon Machine Image (AMI) in 32bit and 64bit 
    architectures. The AMI contains an optimized NumPy/SciPy/Atlas/Blas/Lapack 
    installation compiled for the larger Amazon EC2 instance types. The AMI also comes
    with Sun Grid Engine (SGE) and OpenMPI compiled with SGE support. The public AMI 
    can easily be customized by launching a single instance of the public AMI,
    installing additional software on the instance, and then using StarCluster's 
    "createimage" command to completely automate the process of creating a new AMI from 
    an EC2 instance.
    """,

    download_url='http://web.mit.edu/starcluster',
    license='LGPL3',

    classifiers=[
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: Education',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Clustering',
    ],

)
