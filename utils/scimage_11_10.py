#!/usr/bin/env python
"""
This script is meant to be run inside of a ubuntu cloud image available at
uec-images.ubuntu.com::

    $ EC2_UBUNTU_IMG_URL=http://uec-images.ubuntu.com/oneiric/current
    $ wget $EC2_UBUNTU_IMG_URL/oneiric-server-cloudimg-amd64.tar.gz

or::

    $ wget $EC2_UBUNTU_IMG_URL/oneiric-server-cloudimg-i386.tar.gz

After downloading a Ubuntu cloud image the next step is to extract the image::

    $ tar xvzf oneiric-server-cloudimg-amd64.tar.gz

Then resize it to 10GB::

    $ e2fsck -f oneiric-server-cloudimg-amd64.img
    $ resize2fs oneiric-server-cloudimg-amd64.img 10G

Next you need to mount the image::

    $ mkdir /tmp/img-mount
    $ mount oneiric-server-cloudimg-amd64.img /tmp/img-mount
    $ mount -t proc none /tmp/img-mount/proc
    $ mount -o bind /dev /tmp/img-mount/dev

Copy /etc/resolv.conf and /etc/mtab to the image::

    $ cp /etc/resolv.conf /tmp/img-mount/etc/resolv.conf
    $ grep -v rootfs /etc/mtab > /tmp/img-mount/etc/mtab

Next copy this script inside the image::

    $ cp /path/to/scimage.py /tmp/img-mount/root/scimage.py

Finally chroot inside the image and run this script:

    $ chroot /tmp/img-mount /bin/bash
    $ cd $HOME
    $ python scimage.py
"""

import os
import sys
import glob
import shutil
import fileinput
import subprocess
import multiprocessing

SRC_DIR = "/usr/local/src"
APT_SOURCES_FILE = "/etc/apt/sources.list"
BUILD_UTILS_PKGS = "build-essential devscripts debconf debconf-utils "
BUILD_UTILS_PKGS += "python-setuptools python-pip python-nose"
CLOUD_CFG_FILE = '/etc/cloud/cloud.cfg'
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian maverick-cdh3 contrib'
CONDOR_APT = 'http://www.cs.wisc.edu/condor/debian/development lenny contrib'
NUMPY_SCIPY_SITE_CFG = """\
[DEFAULT]
library_dirs = /usr/lib
include_dirs = /usr/include:/usr/include/suitesparse

[blas_opt]
libraries = ptf77blas, ptcblas, atlas

[lapack_opt]
libraries = lapack, ptf77blas, ptcblas, atlas

[amd]
amd_libs = amd

[umfpack]
umfpack_libs = umfpack

[fftw]
libraries = fftw3
"""
STARCLUSTER_MOTD = """\
#!/bin/sh
cat<<"EOF"
          _                 _           _
__/\_____| |_ __ _ _ __ ___| |_   _ ___| |_ ___ _ __
\    / __| __/ _` | '__/ __| | | | / __| __/ _ \ '__|
/_  _\__ \ || (_| | | | (__| | |_| \__ \ ||  __/ |
  \/ |___/\__\__,_|_|  \___|_|\__,_|___/\__\___|_|

StarCluster Ubuntu 11.10 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://web.mit.edu/starcluster
Documentation: http://web.mit.edu/starcluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: starcluster@mit.edu

This AMI Contains:

  * Custom-Compiled Atlas, Numpy, Scipy, etc
  * Open Grid Scheduler (OGS) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * IPython 0.12 with parallel support
  * and more! (use 'dpkg -l' to show all installed packages)

Open Grid Scheduler/Condor cheat sheet:

  * qstat/condor_q - show status of batch jobs
  * qhost/condor_status- show status of hosts, queues, and jobs
  * qsub/condor_submit - submit batch jobs (e.g. qsub -cwd ./jobscript.sh)
  * qdel/condor_rm - delete batch jobs (e.g. qdel 7)
  * qconf - configure Open Grid Scheduler system

Current System Stats:

EOF

landscape-sysinfo | grep -iv 'graph this data'
"""
CLOUD_INIT_CFG = """\
user: ubuntu
disable_root: 0
preserve_hostname: False
# datasource_list: [ "NoCloud", "OVF", "Ec2" ]

cloud_init_modules:
 - bootcmd
 - resizefs
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - rsyslog
 - ssh

cloud_config_modules:
 - mounts
 - ssh-import-id
 - locale
 - set-passwords
 - grub-dpkg
 - timezone
 - puppet
 - chef
 - mcollective
 - disable-ec2-metadata
 - runcmd

cloud_final_modules:
 - rightscale_userdata
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - keys-to-console
 - final-message

apt_sources:
 - source: deb $MIRROR $RELEASE multiverse
 - source: deb %(CLOUDERA_APT)s
 - source: deb-src %(CLOUDERA_APT)s
 - source: deb %(CONDOR_APT)s
""" % dict(CLOUDERA_APT=CLOUDERA_APT, CONDOR_APT=CONDOR_APT)


def run_command(cmd, ignore_failure=False, failure_callback=None,
                get_output=False):
    kwargs = {}
    if get_output:
        kwargs.update(dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    p = subprocess.Popen(cmd, shell=True, **kwargs)
    output = []
    if get_output:
        line = None
        while line != '':
            line = p.stdout.readline()
            if line != '':
                output.append(line)
                print line,
        for line in p.stderr.readlines():
            if line != '':
                output.append(line)
                print line,
    retval = p.wait()
    if retval != 0:
        errmsg = "command '%s' failed with status %d" % (cmd, retval)
        if failure_callback:
            ignore_failure = failure_callback(retval)
        if not ignore_failure:
            raise Exception(errmsg)
        else:
            sys.stderr.write(errmsg + '\n')
    if get_output:
        return retval, ''.join(output)
    return retval


def apt_command(cmd):
    dpkg_opts = "Dpkg::Options::='--force-confnew'"
    cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
    cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
    run_command(cmd)


def apt_install(pkgs):
    apt_command('install %s' % pkgs)


def chdir(directory):
    opts = glob.glob(directory)
    isdirlist = [o for o in opts if os.path.isdir(o)]
    if len(isdirlist) > 1:
        raise Exception("more than one dir matches: %s" % directory)
    os.chdir(isdirlist[0])


def _fix_atlas_rules(rules_file='debian/rules'):
    for line in fileinput.input(rules_file, inplace=1):
        if 'ATLAS=None' not in line:
            print line,


def configure_apt_sources():
    srcfile = open(APT_SOURCES_FILE)
    contents = srcfile.readlines()
    srcfile.close()
    srclines = []
    for line in contents:
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'deb':
            parts[0] = 'deb-src'
            srclines.append(' '.join(parts).strip())
    srcfile = open(APT_SOURCES_FILE, 'w')
    srcfile.write(''.join(contents))
    srcfile.write('\n'.join(srclines) + '\n')
    srcfile.write('deb %s\n' % CLOUDERA_APT)
    srcfile.write('deb-src %s\n' % CLOUDERA_APT)
    srcfile.write('deb %s\n' % CONDOR_APT)
    srcfile.close()
    run_command('gpg --keyserver keyserver.ubuntu.com --recv-keys 0F932C9C')
    run_command('curl -s %s | sudo apt-key add -' % CLOUDERA_ARCHIVE_KEY)
    apt_install('debian-archive-keyring')


def upgrade_packages():
    apt_command('update')
    apt_command('upgrade')


def install_build_utils():
    """docstring for configure_build"""
    apt_install(BUILD_UTILS_PKGS)


def install_gridscheduler():
    chdir(SRC_DIR)
    apt_command('build-dep gridengine')
    if os.path.isfile('gridscheduler-scbuild.tar.gz'):
        run_command('tar xvzf gridscheduler-scbuild.tar.gz')
        run_command('mv gridscheduler /opt/sge6-fresh')
        return
    apt_install('git')
    run_command('git clone %s' % GRID_SCHEDULER_GIT)
    sts, out = run_command('readlink -f `which java`', get_output=True)
    java_home = out.strip().split('/jre')[0]
    chdir(os.path.join(SRC_DIR, 'gridscheduler', 'source'))
    run_command('git checkout -t -b develop origin/develop')
    env = 'JAVA_HOME=%s' % java_home
    run_command('%s ./aimk -only-depend' % env)
    run_command('%s scripts/zerodepend' % env)
    run_command('%s ./aimk depend' % env)
    run_command('%s ./aimk -no-secure -no-gui-inst' % env)
    sge_root = '/opt/sge6-fresh'
    os.mkdir(sge_root)
    env += ' SGE_ROOT=%s' % sge_root
    run_command('%s scripts/distinst -all -local -noexit -y -- man' % env)


def install_condor():
    chdir(SRC_DIR)
    run_command("rm /var/lock")
    apt_install('condor')
    run_command('ln -s /etc/condor/condor_config /etc/condor_config.local')
    run_command('mkdir /var/lib/condor/log')
    run_command('mkdir /var/lib/condor/run')
    run_command('chown -R condor:condor /var/lib/condor/log')
    run_command('chown -R condor:condor /var/lib/condor/run')


def install_torque():
    chdir(SRC_DIR)
    apt_install('torque-server torque-mom torque-client')


def install_pydrmaa():
    chdir(SRC_DIR)
    run_command('pip install drmaa')


def install_atlas():
    """docstring for install_atlas"""
    chdir(SRC_DIR)
    apt_command('build-dep atlas')
    if glob.glob("*atlas*.deb"):
        run_command('dpkg -i *atlas*.deb')
        return
    apt_command('source atlas')
    chdir('atlas-*')
    run_command('fakeroot debian/rules custom')
    run_command('dpkg -i ../*atlas*.deb')


def install_numpy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-numpy')
    if glob.glob('*numpy*.deb'):
        run_command('dpkg -i *numpy*.deb')
        return
    apt_command('source python-numpy')
    chdir('python-numpy*')
    sitecfg = open('site.cfg', 'w')
    sitecfg.write(NUMPY_SCIPY_SITE_CFG)
    sitecfg.close()
    _fix_atlas_rules()

    def _deb_failure_callback(retval):
        if not glob.glob('../*numpy*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*numpy*.deb')


def install_scipy():
    """docstring for install_scipy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-scipy')
    if glob.glob('*scipy*.deb'):
        run_command('dpkg -i *scipy*.deb')
        return
    apt_command('source python-scipy')
    chdir('python-scipy*')
    sitecfg = open('site.cfg', 'w')
    sitecfg.write(NUMPY_SCIPY_SITE_CFG)
    sitecfg.close()
    _fix_atlas_rules()

    def _deb_failure_callback(retval):
        if not glob.glob('../*numpy*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*scipy*.deb')


def install_openmpi():
    chdir(SRC_DIR)
    apt_command('build-dep libopenmpi-dev')
    apt_install('blcr-util')
    if glob.glob('*openmpi*.deb'):
        run_command('dpkg -i *openmpi*.deb')
        return
    apt_command('source libopenmpi-dev')
    chdir('openmpi*')
    for line in fileinput.input('debian/rules', inplace=1):
        print line,
        if '--enable-heterogeneous' in line:
            print '                        --with-sge \\'

    def _deb_failure_callback(retval):
        if not glob.glob('../*openmpi*.deb'):
            return False
        return True
    run_command('dpkg-buildpackage -rfakeroot -b',
                failure_callback=_deb_failure_callback)
    run_command('dpkg -i ../*openmpi*.deb')
    sts, out = run_command('ompi_info | grep -i grid', get_output=True)
    if 'gridengine' not in out:
        raise Exception("failed to build openmpi with Grid Engine support")


def install_hadoop():
    chdir(SRC_DIR)
    hadoop_pkgs = ['namenode', 'datanode', 'tasktracker', 'jobtracker',
                   'secondarynamenode']
    pkgs = ['hadoop-0.20'] + ['hadoop-0.20-%s' % pkg for pkg in hadoop_pkgs]
    apt_install(' '.join(pkgs))
    run_command('easy_install dumbo')


def install_ipython():
    chdir(SRC_DIR)
    apt_install('libzmq-dev')
    run_command('pip install pyzmq==2.1.9')
    run_command('pip install ipython tornado pygments')
    mjax_install = 'from IPython.external.mathjax import install_mathjax'
    mjax_install += '; install_mathjax()'
    run_command("python -c '%s'" % mjax_install)


def configure_motd():
    for f in glob.glob('/etc/update-motd.d/*'):
        os.unlink(f)
    motd = open('/etc/update-motd.d/00-starcluster', 'w')
    motd.write(STARCLUSTER_MOTD)
    motd.close()
    os.chmod(motd.name, 0755)


def configure_cloud_init():
    """docstring for configure_cloud_init"""
    cloudcfg = open('/etc/cloud/cloud.cfg', 'w')
    cloudcfg.write(CLOUD_INIT_CFG)
    cloudcfg.close()


def configure_bash():
    completion_line_found = False
    for line in fileinput.input('/etc/bash.bashrc', inplace=1):
        if 'bash_completion' in line and line.startswith('#'):
            print line.replace('#', ''),
            completion_line_found = True
        elif completion_line_found:
            print line.replace('#', ''),
            completion_line_found = False
        else:
            print line,
    aliasfile = open('/root/.bash_aliases', 'w')
    aliasfile.write("alias ..='cd ..'\n")
    aliasfile.close()


def setup_environ():
    num_cpus = multiprocessing.cpu_count()
    os.environ['MAKEFLAGS'] = '-j%d' % (num_cpus + 1)
    os.environ['DEBIAN_FRONTEND'] = "noninteractive"


def install_nfs():
    chdir(SRC_DIR)
    run_command('initctl reload-configuration')
    apt_install('nfs-kernel-server')
    run_command('ln -s /etc/init.d/nfs-kernel-server /etc/init.d/nfs')


def install_default_packages():
    # stop mysql for interactively asking for password
    preseedf = '/tmp/mysql-preseed.txt'
    mysqlpreseed = open(preseedf, 'w')
    preseeds = """\
mysql-server mysql-server/root_password select
mysql-server mysql-server/root_password seen true
mysql-server mysql-server/root_password_again select
mysql-server mysql-server/root_password_again seen true
    """
    mysqlpreseed.write(preseeds)
    mysqlpreseed.close()
    run_command('debconf-set-selections < %s' % mysqlpreseed.name)
    run_command('rm %s' % mysqlpreseed.name)
    pkgs = "python-dev git vim mercurial subversion cvs encfs "
    pkgs += "openmpi-bin libopenmpi-dev python-django "
    pkgs += "keychain screen tmux zsh ksh csh tcsh python-mpi4py "
    pkgs += "python-virtualenv python-imaging python-boto python-matplotlib "
    pkgs += "unzip rar unace build-essential gfortran ec2-api-tools "
    pkgs += "ec2-ami-tools mysql-server mysql-client apache2 "
    pkgs += "libapache2-mod-wsgi sysv-rc-conf pssh emacs cython irssi "
    pkgs += "python-distutils-extra htop vim-scripts python-ctypes python-pudb"
    apt_install(pkgs)


def configure_init():
    for script in ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql']:
        run_command('find /etc/rc* -iname \*%s\* -delete' % script)


def cleanup():
    run_command('rm /etc/resolv.conf')
    run_command('rm /etc/mtab')
    run_command('rm -rf /root/*')
    exclude = ['/root/.bashrc', '/root/.profile', '/root/.bash_aliases']
    for dot in glob.glob("/root/.*"):
        if dot not in exclude:
            run_command('rm -rf %s' % dot)
    for path in glob.glob('/usr/local/src/*'):
        if os.path.isdir(path):
            shutil.rmtree(path)
    run_command('rm -f /var/cache/apt/archives/*.deb')
    run_command('rm -f /var/cache/apt/archives/partial/*')
    for f in glob.glob('/etc/profile.d'):
        if 'byobu' in f:
            run_command('rm %s' % f)


def main():
    """docstring for main"""
    if os.getuid() != 0:
        sys.stderr.write('you must be root to run this script\n')
        return
    setup_environ()
    configure_motd()
    configure_cloud_init()
    configure_bash()
    configure_apt_sources()
    upgrade_packages()
    install_build_utils()
    install_gridscheduler()
    install_condor()
    #install_torque()
    install_pydrmaa()
    install_atlas()
    install_numpy()
    install_scipy()
    install_ipython()
    install_openmpi()
    install_hadoop()
    install_nfs()
    install_default_packages()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()
