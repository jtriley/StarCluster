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
BUILD_UTILS_PKGS += "python-dev python-setuptools python-pip python-nose rar "
BUILD_UTILS_PKGS += "python-distutils-extra gfortran unzip unace cdbs patch "
CLOUD_CFG_FILE = '/etc/cloud/cloud.cfg'
GRID_SCHEDULER_GIT = 'git://github.com/jtriley/gridscheduler.git'
CLOUDERA_ARCHIVE_KEY = 'http://archive.cloudera.com/debian/archive.key'
CLOUDERA_APT = 'http://archive.cloudera.com/debian squeeze-cdh3u5 contrib'
PPAS = ["ppa:staticfloat/julia-deps", "ppa:justin-t-riley/starcluster"]
STARCLUSTER_MOTD = """\
#!/bin/sh
cat<<"EOF"
          _                 _           _
__/\_____| |_ __ _ _ __ ___| |_   _ ___| |_ ___ _ __
\    / __| __/ _` | '__/ __| | | | / __| __/ _ \ '__|
/_  _\__ \ || (_| | | | (__| | |_| \__ \ ||  __/ |
  \/ |___/\__\__,_|_|  \___|_|\__,_|___/\__\___|_|

StarCluster Ubuntu 13.04 AMI
Software Tools for Academics and Researchers (STAR)
Homepage: http://star.mit.edu/cluster
Documentation: http://star.mit.edu/cluster/docs/latest
Code: https://github.com/jtriley/StarCluster
Mailing list: http://star.mit.edu/cluster/mailinglist.html

This AMI Contains:

  * Open Grid Scheduler (OGS - formerly SGE) queuing system
  * Condor workload management system
  * OpenMPI compiled with Open Grid Scheduler support
  * OpenBLAS - Highly optimized Basic Linear Algebra Routines
  * NumPy/SciPy linked against OpenBlas
  * Pandas - Data Analysis Library
  * IPython 1.1.0 with parallel and notebook support
  * Julia 0.2prerelease with IJulia
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
""" % dict(CLOUDERA_APT=CLOUDERA_APT)


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
    with open(APT_SOURCES_FILE, 'w') as srcfile:
        srcfile.write(''.join(contents))
        srcfile.write('\n'.join(srclines) + '\n')
    with open('/etc/apt/sources.list.d/cloudera-hadoop.list', 'w') as srcfile:
        srcfile.write('deb %s\n' % CLOUDERA_APT)
        srcfile.write('deb-src %s\n' % CLOUDERA_APT)
    run_command('gpg --keyserver keyserver.ubuntu.com --recv-keys 0F932C9C')
    run_command('curl -s %s | sudo apt-key add -' % CLOUDERA_ARCHIVE_KEY)
    apt_install('debian-archive-keyring')
    for ppa in PPAS:
        run_command('add-apt-repository %s -y -s' % ppa)


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
    run_command("rm -f /var/lock")
    #apt_install('condor=7.7.2-1')
    #run_command('echo condor hold | dpkg --set-selections')
    #run_command('ln -s /etc/condor/condor_config /etc/condor_config.local')
    #run_command('mkdir /var/lib/condor/log')
    #run_command('mkdir /var/lib/condor/run')
    #run_command('chown -R condor:condor /var/lib/condor/log')
    #run_command('chown -R condor:condor /var/lib/condor/run')
    apt_install('condor')


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


def install_openblas():
    """docstring for install_openblas"""
    chdir(SRC_DIR)
    apt_command('build-dep libopenblas-dev')
    if glob.glob("*openblas*.deb"):
        run_command('dpkg -i *openblas*.deb')
    else:
        apt_command('source libopenblas-dev')
        chdir('openblas-*')
        rule_file = open('Makefile.rule', 'a')
        # NO_AFFINITY=1 is required to utilize all cores on all non
        # cluster-compute/GPU instance types due to the shared virtualization
        # layer not supporting processor affinity properly. However, Cluster
        # Compute/GPU instance types use a near-bare-metal hypervisor which
        # *does* support processor affinity. From minimal testing it appears
        # that there is a ~20% increase in performance when using affinity on
        # cc1/cg1 types implying NO_AFFINITY=1 should *not* be set for cluster
        # compute/GPU AMIs.
        lines = ['DYNAMIC_ARCH=1', 'NUM_THREADS=64', 'NO_LAPACK=1',
                 'NO_AFFINITY=1']
        rule_file.write('\n'.join(lines))
        rule_file.close()
        run_command('fakeroot debian/rules custom')
        run_command('dpkg -i ../*openblas*.deb')
    run_command('echo libopenblas-base hold | dpkg --set-selections')
    run_command('echo libopenblas-dev hold | dpkg --set-selections')
    run_command("ldconfig")


def install_python_packages():
    install_pydrmaa()
    install_numpy_scipy()
    install_pandas()
    install_ipython()
    apt_command('build-dep python-imaging')
    pkgs = "virtualenv pillow boto matplotlib django mpi4py ctypes Cython "
    pkgs += "pudb supervisor "
    run_command("pip install %s" % pkgs)


def install_numpy_scipy():
    """docstring for install_numpy"""
    chdir(SRC_DIR)
    apt_command('build-dep python-numpy')
    apt_command('build-dep python-scipy')
    run_command('pip install -d . numpy')
    run_command('tar xvzf numpy*.tar.gz')
    run_command("sed -i 's/return None #/pass #/' numpy*/numpy/core/setup.py")
    run_command("cd numpy* && python setup.py install")
    run_command('pip install scipy')


def install_pandas():
    """docstring for install_pandas"""
    chdir(SRC_DIR)
    apt_command('build-dep pandas')
    run_command('pip install pandas')


def install_openmpi():
    chdir(SRC_DIR)
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
    run_command('ldconfig')


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
    run_command('pip install ipython[parallel,notebook]')
    # This is broken in IPy 1.1.0
    #mjax_install = 'from IPython.external.mathjax import install_mathjax'
    #mjax_install += '; install_mathjax()'
    #run_command("python -c '%s'" % mjax_install)


def install_julia():
    chdir(SRC_DIR)
    apt_install('zlib1g-dev patchelf llvm-3.3-dev libsuitesparse-dev '
                'libncurses5-dev libopenblas-dev liblapack-dev '
                'libarpack2-dev libfftw3-dev libgmp-dev libpcre3-dev '
                'libunwind8-dev libreadline-dev libdouble-conversion-dev '
                'libopenlibm-dev librmath-dev libmpfr-dev')
    run_command('git clone git://github.com/JuliaLang/julia.git')
    buildopts = 'LLVM_CONFIG=llvm-config-3.3 VERBOSE=1 USE_BLAS64=0 '
    libs = ['LLVM', 'ZLIB', 'SUITESPARSE', 'ARPACK', 'BLAS', 'FFTW', 'LAPACK',
            'GMP', 'MPFR', 'PCRE', 'LIBUNWIND', 'READLINE', 'GRISU',
            'OPENLIBM', 'RMATH']
    buildopts += ' '.join(['USE_SYSTEM_%s=1' % lib for lib in libs])
    run_command('cd julia && make %s PREFIX=/usr install' % buildopts)


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
    pkgs = "git vim mercurial subversion cvs encfs keychain screen tmux zsh "
    pkgs += "ksh csh tcsh ec2-api-tools ec2-ami-tools mysql-server "
    pkgs += "mysql-client apache2 libapache2-mod-wsgi nginx sysv-rc-conf "
    pkgs += "pssh emacs irssi htop vim-scripts mosh default-jdk mpich2 xvfb "
    pkgs += "openmpi-bin libopenmpi-dev libopenblas-dev liblapack-dev"
    apt_install(pkgs)


def configure_init():
    scripts = ['nfs-kernel-server', 'hadoop', 'condor', 'apache', 'mysql',
               'nginx']
    for script in scripts:
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
    install_nfs()
    install_default_packages()
    install_python_packages()
    # Only use these to build the packages locally
    # These should normally be installed from the StarCluster PPA
    #install_openblas()
    #install_openmpi()
    install_julia()
    install_gridscheduler()
    install_condor()
    install_hadoop()
    configure_init()
    cleanup()

if __name__ == '__main__':
    main()
