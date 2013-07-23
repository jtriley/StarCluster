#!/usr/bin/env python
"""
This script is meant to be run inside of a ubuntu cloud image available at
uec-images.ubuntu.com::

    $ EC2_UBUNTU_IMG_URL=http://uec-images.ubuntu.com/precise/current
    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-amd64.tar.gz

or::

    $ wget $EC2_UBUNTU_IMG_URL/precise-server-cloudimg-i386.tar.gz

After downloading a Ubuntu cloud image the next step is to extract the image::

    $ tar xvzf precise-server-cloudimg-amd64.tar.gz

Then resize it to 10GB::

    $ e2fsck -f precise-server-cloudimg-amd64.img
    $ resize2fs precise-server-cloudimg-amd64.img 10G

Next you need to mount the image::

    $ mkdir /tmp/img-mount
    $ mount precise-server-cloudimg-amd64.img /tmp/img-mount
    $ mount -t proc none /tmp/img-mount/proc
    $ mount -t sysfs none /tmp/img-mount/sys
    $ mount -o bind /dev /tmp/img-mount/dev
    $ mount -t devpts none /tmp/img-mount/dev/pts
    $ mount -o rbind /var/run/dbus /tmp/img-mount/var/run/dbus

Copy /etc/resolv.conf and /etc/mtab to the image::

    $ mkdir -p /tmp/img-mount/var/run/resolvconf
    $ cp /etc/resolv.conf /tmp/img-mount/var/run/resolvconf/resolv.conf
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
BUILD_UTILS_PKGS = "build-essential devscripts debconf debconf-utils dpkg-dev "
BUILD_UTILS_PKGS += "gfortran llvm-3.2-dev swig cdbs patch python-dev "
BUILD_UTILS_PKGS += "python-distutils-extra python-setuptools python-pip "
BUILD_UTILS_PKGS += "python-nose"
CLOUD_CFG_FILE = '/etc/cloud/cloud.cfg'
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian maverick-cdh3u5 contrib'
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

StarCluster Ubuntu 12.04 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://star.mit.edu/cluster
Documentation: http://star.mit.edu/cluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: starcluster@mit.edu

This AMI Contains:

  * Open Grid Scheduler (OGS - formerly SGE) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * OpenBLAS - Highly optimized Basic Linear Algebra Routines
  * NumPy/SciPy linked against OpenBlas
  * IPython 0.13 with parallel and notebook support
  * and more! (use 'dpkg -l' to show all installed packages)

Open Grid Scheduler/Condor cheat sheet:

  * qstat/condor_q - show status of batch jobs
  * qhost/condor_status- show status of hosts, queues, and jobs
  * qsub/condor_submit - submit batch jobs (e.g. qsub -cwd ./job.sh)
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
    run_command('add-apt-repository ppa:staticfloat/julia-deps -y')
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
    apt_install('condor=7.7.2-1')
    run_command('echo condor hold | dpkg --set-selections')
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


def install_blas_lapack():
    """docstring for install_openblas"""
    chdir(SRC_DIR)
    apt_install("libopenblas-dev")


def install_numpy_scipy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    run_command('pip install -d . numpy')
    run_command('unzip numpy*.zip')
    run_command("sed -i 's/return None #/pass #/' numpy*/numpy/core/setup.py")
    run_command('pip install scipy')


def install_pandas():
    """docstring for install_pandas"""
    chdir(SRC_DIR)
    apt_command('build-dep pandas')
    run_command('pip install pandas')


def install_matplotlib():
    chdir(SRC_DIR)
    run_command('pip install matplotlib')


def install_julia():
    apt_install("libsuitesparse-dev libncurses5-dev "
                "libopenblas-dev libarpack2-dev libfftw3-dev libgmp-dev "
                "libunwind7-dev libreadline-dev zlib1g-dev")
    buildopts = """\
BUILDOPTS="LLVM_CONFIG=llvm-config-3.2 USE_QUIET=0 USE_LIB64=0"; for lib in \
LLVM ZLIB SUITESPARSE ARPACK BLAS FFTW LAPACK GMP LIBUNWIND READLINE GLPK \
NGINX; do export BUILDOPTS="$BUILDOPTS USE_SYSTEM_$lib=1"; done"""
    chdir(SRC_DIR)
    if not os.path.exists("julia"):
        run_command("git clone git://github.com/JuliaLang/julia.git")
    run_command("%s && cd julia && make $BUILDOPTS PREFIX=/usr install" %
                buildopts)


def install_mpi():
    chdir(SRC_DIR)
    apt_install('mpich2')
    apt_command('build-dep openmpi')
    apt_install('blcr-util')
    if glob.glob('*openmpi*.deb'):
        run_command('dpkg -i *openmpi*.deb')
    else:
        apt_command('source openmpi')
        chdir('openmpi*')
        for line in fileinput.input('debian/rules', inplace=1):
            print line,
            if '--enable-heterogeneous' in line:
                print '                        --with-sge \\'

        def _deb_failure_callback(retval):
            if not glob.glob('../*openmpi*.deb'):
                return False
            return True
        run_command('dch --local=\'+custom\' '
                    '"custom build on: `uname -s -r -v -m -p -i -o`"')
        run_command('dpkg-buildpackage -rfakeroot -b',
                    failure_callback=_deb_failure_callback)
        run_command('dpkg -i ../*openmpi*.deb')
    sts, out = run_command('ompi_info | grep -i grid', get_output=True)
    if 'gridengine' not in out:
        raise Exception("failed to build OpenMPI with "
                        "Open Grid Scheduler support")
    run_command('echo libopenmpi1.3 hold | dpkg --set-selections')
    run_command('echo libopenmpi-dev hold | dpkg --set-selections')
    run_command('echo libopenmpi-dbg hold | dpkg --set-selections')
    run_command('echo openmpi-bin hold | dpkg --set-selections')
    run_command('echo openmpi-checkpoint hold | dpkg --set-selections')
    run_command('echo openmpi-common hold | dpkg --set-selections')
    run_command('echo openmpi-doc hold | dpkg --set-selections')
    run_command('pip install mpi4py')


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
    run_command('pip install ipython tornado pygments pyzmq')
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
    if os.path.isfile('/sbin/initctl') and not os.path.islink('/sbin/initctl'):
        run_command('mv /sbin/initctl /sbin/initctl.bak')
        run_command('ln -s /bin/true /sbin/initctl')


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
    pkgs = ["git", "mercurial", "subversion", "cvs", "vim",  "vim-scripts",
            "emacs", "tmux", "screen", "zsh", "ksh", "csh", "tcsh", "encfs",
            "keychain", "unzip", "rar", "unace", "ec2-api-tools",
            "ec2-ami-tools", "mysql-server", "mysql-client", "apache2",
            "libapache2-mod-wsgi", "sysv-rc-conf", "pssh", "cython", "irssi",
            "htop", "mosh", "default-jdk", "xvfb", "python-imaging",
            "python-ctypes"]
    apt_install(' '.join(pkgs))


def install_python_packges():
    pypkgs = ['python-boto', 'python-paramiko', 'python-django',
              'python-pudb']
    for pypkg in pypkgs:
        if pypkg.startswith('python-'):
            apt_command('build-dep %s' % pypkg.split('python-')[1])
        run_command('pip install %s')


def configure_init():
    for script in ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql']:
        run_command('find /etc/rc* -iname \*%s\* -delete' % script)


def cleanup():
    run_command('rm -f /etc/resolv.conf')
    run_command('rm -rf /var/run/resolvconf')
    run_command('rm -f /etc/mtab')
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
            run_command('rm -f %s' % f)
    if os.path.islink('/sbin/initctl') and os.path.isfile('/sbin/initctl.bak'):
        run_command('mv -f /sbin/initctl.bak /sbin/initctl')


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
    install_default_packages()
    install_gridscheduler()
    install_condor()
    #install_torque()
    install_pydrmaa()
    install_blas_lapack()
    install_numpy_scipy()
    install_matplotlib()
    install_pandas()
    install_ipython()
    install_mpi()
    install_hadoop()
    install_nfs()
    install_julia()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()
