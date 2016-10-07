#!/usr/bin/env python
# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import sys

if sys.version_info < (2, 6):
    error = "ERROR: StarCluster requires Python 2.6+ ... exiting."
    print >> sys.stderr, error
    sys.exit(1)

try:
    from setuptools import setup, find_packages
    from setuptools.command.test import test as TestCommand

    class PyTest(TestCommand):
        user_options = TestCommand.user_options[:]
        user_options += [
            ('live', 'L', 'Run live StarCluster tests on a real AWS account'),
            ('coverage', 'C', 'Produce a coverage report for StarCluster'),
        ]

        def initialize_options(self):
            TestCommand.initialize_options(self)
            self.live = None
            self.coverage = None

        def finalize_options(self):
            TestCommand.finalize_options(self)
            self.test_suite = True
            self.test_args = []
            if self.coverage:
                self.test_args.append('--coverage')
            if self.live:
                self.test_args.append('--live')

        def run_tests(self):
            # import here, cause outside the eggs aren't loaded
            import pytest
            # Needed in order for pytest_cache to load properly
            # Alternate fix: import pytest_cache and pass to pytest.main
            import _pytest.config
            pm = _pytest.config.get_plugin_manager()
            pm.consider_setuptools_entrypoints()
            errno = pytest.main(self.test_args)
            sys.exit(errno)

    console_scripts = ['starcluster = starcluster.cli:main']
    extra = dict(test_suite="starcluster.tests",
                 tests_require= ["pytest-cov==1.8", "pytest-pep8",
                                 "pytest-flakes", "pytest"],
                 cmdclass={"test": PyTest},
                 install_requires=["paramiko>=1.12.1", "boto>=2.23.0",
                                   "workerpool>=0.9.2", "Jinja2>=2.7",
                                   "decorator>=3.4.0", "iptools>=0.6.1",
                                   "optcomplete>=1.2-devel",
                                   "pycrypto>=2.5", "scp>=0.7.1",
                                   "iso8601>=0.1.8"],
                 include_package_data=True,
                 entry_points=dict(console_scripts=console_scripts),
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
                isdir = os.path.isdir(fn)
                has_init = os.path.isfile(os.path.join(fn, '__init__.py'))
                if '.' not in name and isdir and has_init:
                    out.append(prefix + name)
                    stack.append((fn, prefix + name + '.'))
        for pat in list(exclude) + ['ez_setup', 'distribute_setup']:
            from fnmatch import fnmatchcase
            out = [item for item in out if not fnmatchcase(item, pat)]
        return out

    extra = {'scripts': ['bin/starcluster']}

VERSION = 0.9999
static = os.path.join('starcluster', 'static.py')
execfile(static)  # pull VERSION from static.py

README = open('README.rst').read()

setup(
    name='StarCluster',
    version=VERSION,
    packages=find_packages(),
    package_data={'starcluster.templates':
                  ['web/*.*', 'web/css/*', 'web/js/*']},
    license='LGPL3',
    author='Justin Riley',
    author_email='justin.t.riley@gmail.com',
    url="http://star.mit.edu/cluster",
    description="StarCluster is a utility for creating and managing computing "
    "clusters hosted on Amazon's Elastic Compute Cloud (EC2).",
    long_description=README,
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Topic :: Education',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Clustering',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    **extra
)
