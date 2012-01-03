#!/usr/bin/env python
import os
import sys
import time
import string
import optparse

from starcluster import config
from starcluster import cluster
from starcluster import spinner
from starcluster import exception
from starcluster import logger
logger.configure_sc_logging()
log = logger.log


def deploy_img(img_path, vol_size, arch, region, src_ami, dev=None,
               kernel_id=None, ramdisk_id=None, platform=None,
               remove_old=False, **cluster_kwargs):
    """
    Deploy a filesystem image as a new AMI in a given region.

    This method creates a 1-node host cluster in the desired `region`, copies
    the filesystem image to the cluster, creates and attaches a new EBS volume
    with size `vol_size`, installs the image onto the new EBS volume, creates a
    snapshot of the resulting volume and registers a new AMI in the `region`.
    """
    cfg = config.StarClusterConfig().load()
    ec2 = cfg.get_easy_ec2()
    ec2.connect_to_region(region)
    src_img = ec2.get_image(src_ami)
    kernel_id = kernel_id or src_img.kernel_id
    ramdisk_id = ramdisk_id or src_img.ramdisk_id
    itypemap = dict(i386='m1.small', x86_64='m1.large')
    dev = dev or dict(i386='/dev/sdj', x86_64='/dev/sdz')[arch]
    cm = cluster.ClusterManager(cfg, ec2)
    try:
        log.info("Checking for existing imghost cluster")
        cl = cm.get_cluster('imghost')
        log.info("Using existing imghost cluster")
    except exception.ClusterDoesNotExist:
        log.info("No imghost cluster found, creating...")
        default = cm.get_default_cluster_template()
        cl = cm.get_cluster_template(default, 'imghost')
        keys = ec2.get_keypairs()
        key = None
        for k in keys:
            if cfg.keys.has_key(k.name):
                key = cfg.keys.get(k.name)
                key['keyname'] = k.name
                break
        if key:
            cluster_kwargs.update(key)
        hostitype = itypemap[src_img.architecture]
        cluster_kwargs.update(dict(cluster_size=1, cluster_shell="bash",
                                   node_image_id=src_ami,
                                   node_instance_type=hostitype))
        cl.update(cluster_kwargs)
        cl.start(create_only=True, validate=True)
    cl.wait_for_cluster()
    host = cl.master_node
    log.info("Copying %s to /mnt on master..." % img_path)
    host.ssh.put(img_path, '/mnt/')
    bname = os.path.basename(img_path)
    if bname.endswith('.tar.gz'):
        log.info("Extracting image(s)...")
        host.ssh.execute('cd /mnt && tar xvzf %s' % bname)
        bname = bname.replace('.tar.gz', '')
    if not host.ssh.isfile('/mnt/%s' % bname):
        raise exception.BaseException("/mnt/%s does not exist" % bname)
    log.info("Creating EBS volume")
    vol = ec2.create_volume(vol_size, host.placement)
    log.info("Attaching EBS volume %s to master as %s" % (vol.id, dev))
    vol.attach(host.id, dev)
    log.info("Waiting for drive to attach...")
    s = spinner.Spinner()
    s.start()
    realdev = '/dev/xvd%s' % dev[-1]
    while not host.ssh.path_exists(realdev):
        time.sleep(10)
    s.stop()
    log.info("Installing image on volume %s ..." % vol.id)
    host.ssh.execute("cat /mnt/%s > %s" % (bname, realdev))
    log.info("Checking filesystem...")
    host.ssh.execute("e2fsck -pf %s" % realdev)
    log.info("Resizing filesystem to fit EBS volume...")
    host.ssh.execute("resize2fs %s" % realdev)
    vol.detach()
    while vol.update() != 'available':
        time.sleep(10)
    xarch = arch
    if xarch == 'i386':
        xarch = 'x86'
    snapdesc = 'StarCluster %s %s EBS AMI Snapshot' % (platform, xarch)
    snap = ec2.create_snapshot(vol, description=snapdesc, wait_for_snapshot=True)
    vol.delete()
    bmap = ec2.create_root_block_device_map(snap.id, add_ephemeral_drives=True)
    imgname = string.lower(platform.replace(' ', '-'))
    imgname = 'starcluster-base-%s-%s' % (imgname, xarch)
    imgdesc = 'StarCluster Base %s %s (%s)' % (platform, xarch,
                                               string.capitalize(region))
    oldimg = ec2.get_images(filters=dict(name=imgname))
    if oldimg:
        oldimg = oldimg[0]
        oldsnap = ec2.get_snapshot(oldimg.block_device_mapping['/dev/sda1'].snapshot_id)
        if remove_old:
            log.info("Deregistering old AMI: %s" % oldimg.id)
            oldimg.deregister()
            log.info("Deleting old snapshot: %s" % oldsnap.id)
            oldsnap.delete()
        else:
            log.info("Existing image %s already has name '%s'" %
                     (oldimg.id, imgname))
            log.info("Please remove old image %s and snapshot %s" %
                     (oldimg.id, oldsnap.id))
            log.info("Then register new AMI with snapshot %s and name '%s'" %
                     (snap.id, imgname))
            return
    img = ec2.register_image(name=imgname, description=imgdesc,
                             architecture=arch, kernel_id=kernel_id,
                             ramdisk_id=ramdisk_id,
                             root_device_name='/dev/sda1',
                             block_device_map=bmap)
    return img

def main():
    parser = optparse.OptionParser('deploy disk image to region')
    parser.usage = '%s [options] <img_path> <vol_size> <img_arch> '
    parser.usage += '<region> <src_ami>'
    parser.usage = parser.usage % sys.argv[0]
    parser.add_option('-d', '--device', action="store", dest='dev',
                      default=None, help="device to attach volume to"
                      "(defaults to /dev/sdj for 32bit, /dev/sdz for 64bit)")
    parser.add_option('-k', '--kernel-id', action="store", dest='kernel_id',
                      default=None, help="kernel to use for AMI (defaults to "
                      "same as src_ami)")
    parser.add_option('-r', '--ramdisk-id', action="store", dest='ramdisk_id',
                      default=None, help="ramdisk to use for AMI (defaults to "
                      "same as src_ami)")
    parser.add_option('-R', '--remove-old-ami', action="store_true",
                      dest='remove_old', default=False,
                      help="remove any AMI with same name as generated AMI")
    parser.add_option('-p', '--platform', action="store", dest='platform',
                      default=None, help="platform name (e.g. Ubuntu 11.10)")
    opts, args = parser.parse_args()
    if len(args) != 5:
        parser.error('not enough arguments specified (pass --help for usage)')
    img_path, vol_size, arch, region, src_ami = args
    size_err = 'vol_size must be an integer > 0'
    try:
        vol_size = int(vol_size)
        if vol_size <= 0:
            parser.error(size_err)
    except ValueError:
            parser.error(size_err)
    if not os.path.exists(img_path):
        parser.error('img_path %s does not exist' % img_path)
    arches = ['i386', 'x86_64']
    if arch not in arches:
        parser.error('arch must be one of: %s' % ', '.join(arches))
        return False
    try:
        deploy_img(*args, **opts.__dict__)
    except exception.BaseException, e:
        log.error(e)

if __name__ == '__main__':
    main()
