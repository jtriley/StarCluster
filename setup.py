#!/usr/bin/env python
import os
import sys

if sys.version_info < (2, 5):
    error = "ERROR: StarCluster requires Python 2.5+ ... exiting."
    print >> sys.stderr, error
    sys.exit(1)

try:
    from setuptools import setup, find_packages
    extra = dict(test_suite="starcluster.tests",
                 tests_require="nose",
                 install_requires=["paramiko==1.7.7.1", "boto==2.0",
                                   "workerpool==0.9.2", "Jinja2==2.5.5",
                                   "decorator==3.3.1"],
                 zip_safe=False)
except ImportError:
    import string
    from distutils.core import setup

    def convert_path(pathname):
        """
        Local copy of setuptools.convert_path used by find_packages (only used
        with distutils which is missing the find_packages feature)
        """
        if os.sep == '/':
            return pathname
        if not pathname:
            return pathname
        if pathname[0] == '/':
            raise ValueError("path '%s' cannot be absolute" % pathname)
        if pathname[-1] == '/':
            raise ValueError("path '%s' cannot end with '/'" % pathname)
        paths = string.split(pathname, '/')
        while '.' in paths:
            paths.remove('.')
        if not paths:
            return os.curdir
        return os.path.join(*paths)

    def find_packages(where='.', exclude=()):
        """
        Local copy of setuptools.find_packages (only used with distutils which
        is missing the find_packages feature)
        """
        out = []
        stack = [(convert_path(where), '')]
        while stack:
            where, prefix = stack.pop(0)
            for name in os.listdir(where):
                fn = os.path.join(where, name)
                if ('.' not in name and os.path.isdir(fn) and
                    os.path.isfile(os.path.join(fn, '__init__.py'))):
                    out.append(prefix + name)
                    stack.append((fn, prefix + name + '.'))
        for pat in list(exclude) + ['ez_setup', 'distribute_setup']:
            from fnmatch import fnmatchcase
            out = [item for item in out if not fnmatchcase(item, pat)]
        return out

    extra = {}

VERSION = 0.9999
static = os.path.join('starcluster', 'static.py')
execfile(static)  # pull VERSION from static.py

setup(
    name='StarCluster',
    version=VERSION,
    packages=find_packages(),
    package_data={'starcluster.templates':
                  ['web/*.*', 'web/css/*', 'web/js/*']},
    scripts=['bin/starcluster'],
    license='LGPL3',
    author='Justin Riley',
    author_email='justin.t.riley@gmail.com',
    url="http://web.mit.edu/starcluster",
    description="StarCluster is a utility for creating and managing computing "
    "clusters hosted on Amazon's Elastic Compute Cloud (EC2).",
    long_description="""
    StarCluster is a utility for creating and managing computing clusters
    hosted on Amazon's Elastic Compute Cloud (EC2). StarCluster utilizes
    Amazon's EC2 web service to create and destroy clusters of Linux virtual
    machines on demand.

    To get started, the user creates a simple configuration file with their AWS
    account details and a few cluster preferences (e.g. number of machines,
    machine type, ssh keypairs, etc). After creating the configuration file and
    running StarCluster's "start" command, a cluster of Linux machines
    configured with the Sun Grid Engine queuing system, an NFS-shared /home
    directory, and OpenMPI with password-less ssh is created and ready to go
    out-of-the-box. Running StarCluster's "stop" command will shutdown the
    cluster and stop paying for service. This allows the user to only pay for
    what they use.

    StarCluster can also utilize Amazon's Elastic Block Storage (EBS) volumes
    to provide persistent data storage for a cluster. EBS volumes allow you to
    store large amounts of data in the Amazon cloud and are also easy to
    back-up and replicate in the cloud.  StarCluster will mount and NFS-share
    any volumes specified in the config. StarCluster's "createvolume" command
    provides the ability to automatically create, format, and partition new EBS
    volumes for use with StarCluster.

    StarCluster provides a Ubuntu-based Amazon Machine Image (AMI) in 32bit and
    64bit architectures. The AMI contains an optimized NumPy, SciPy, Atlas,
    Blas, Lapack installation compiled for the larger Amazon EC2 instance
    types. The AMI also comes with Sun Grid Engine (SGE) and OpenMPI compiled
    with SGE support. The public AMI can easily be customized by launching a
    single instance of the public AMI, installing additional software on the
    instance, and then using StarCluster's "createimage" command to completely
    automate the process of creating a new AMI from an EC2 instance.
    """,
    classifiers=[
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Library or Lesser General Public '
        'License (LGPL)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: Education',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Clustering',
    ],
    **extra
)
