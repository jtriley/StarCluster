#!/usr/bin/env python
import os
import sys

from starcluster.config import StarClusterConfig

print 'Simple wrapper script for s3fs (http://s3fs.googlecode.com/)'

cfg = StarClusterConfig().load()
ec2 = cfg.get_easy_ec2()
buckets = ec2.s3.get_buckets()
counter = 0
for bucket in buckets:
    print "[%d] %s" % (counter,bucket.name)
    counter += 1

try:
    inp = int(raw_input('>>> Enter the bucket to mnt: '))
    selection = buckets[inp].name
    print 'you selected: %s' % selection
    mountpt = raw_input('>>> please enter the mnt point: ')
    print 'mounting %s at: %s' % (selection,mountpt)
except KeyboardInterrupt,e:
    print
    print 'Exiting...'
    sys.exit(1)

try:
    os.system('s3fs %s -o accessKeyId=%s -o secretAccessKey=%s %s' % (selection,
                                                                      cfg.aws.get('aws_access_key_id'),
                                                                      cfg.aws.get('aws_secret_access_key'),mountpt))
except KeyboardInterrupt,e:
    print
    print 'Attempting to umount %s' % mountpt
    os.system('sudo umount %s' % mountpt)
    print 'Exiting...'
    sys.exit(1)
