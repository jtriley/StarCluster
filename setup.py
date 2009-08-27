#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'StarCluster',
    version = '0.90',
    packages = ['starcluster', 'starcluster.templates'],
    package_dir = {'starcluster':'starcluster'},
    scripts=['bin/starcluster',],

    install_requires=[
        "paramiko",
    ],

    zip_safe = True,

    author='Justin Riley',
    author_email='justin.t.riley@gmail.com',
    url="http://web.mit.edu/starcluster",
    description="StarCluster is a utility for creating and managing general purpose computing clusters hosted on Amazon's Elastic Compute Cloud (EC2).",
    long_description = """
    StarCluster minimizes the administrative overhead associated with obtaining, 
    configuring, and managing a traditional computing cluster used in research labs 
    or for general distributed computing applications. 
    
    StarCluster is built on top of EC2 which enables dynamically creating and 
    destroying clusters of virtual machines and only paying for the time used. 
    The amount per hour varies depending on the instance type and the number of 
    virtual machines. 

    StarCluster consists of a library and set of scripts that use the library. For end-users, 
    the scripts are the main user interface and provide simple intuitive options for getting 
    started with distributed computing on EC2 (i.e. starting/stopping clusters, managing 
    software configurations, etc). For developers, the library wraps the EC2 API to provide 
    a simplified interface for launching/terminating nodes, executing commands on the nodes,  
    copying files to/from the nodes, etc.

    To get started, the user creates a simple configuration file with their account 
    details and a few preferences (i.e. number of machines, instance type, EBS 
    volumes to be mounted, etc). After creating the configuration file and starting 
    the software, a cluster of Linux machines configured with a queuing 
    system, a nfs shared /home directory, and OpenMPI is created and ready to 
    go out of the box.

    StarCluster has been targeted for computational research labs and to support 
    classrooms with computational requirements. 

    For research labs, StarCluster is a way for graduate students and faculty to have
    an on-demand cluster.  This means students can access their research with the same hardware
    and software configurations wherever they go; even if they move to another institution. 
    StarCluster also provides a way for students to experiment with a computational model 
    on a cheap budget before running on local dedicated resources.

    In the classroom, StarCluster provides a cost effective, reliable way of managing the 
    software configurations for a particular course. It also removes the majority of system 
    administration concerns since the initial setup procedures have been captured in StarCluster 
    and in the user's software configurations (i.e. AMI images, EBS volumes, etc). This means 
    that each semester the exact computing cluster configuration can be recalled with more or 
    less nodes. With this model there is also the benefit that if hardware problems occur 
    it's easy to request a new set of machines in the cloud.
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
