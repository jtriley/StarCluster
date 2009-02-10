#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'python-cuda',
    version = '0.0.1',
    packages = ['molsim'],
    package_dir = {'cuda':'cuda'},
    scripts=['bin/manage-cluster.py'],
    author='Justin Riley',
    author_email='justin.t.riley@gmail.com',
    url='',
    description='Python library for launching an NFS/MPI/SGE EC2 cluster configured for StarMolsim',
    long_description = """ """,
    download_url='',
    license='GPL2',
)
