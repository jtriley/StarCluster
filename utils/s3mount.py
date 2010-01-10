#!/usr/bin/env python
import os

from starcluster.config import StarClusterConfig

print 'Simple wrapper script for s3fs (http://s3fs.googlecode.com/)'

cfg = StarClusterConfig(); cfg.load()
ec2 = cfg.get_easy_ec2()
buckets = ec2.s3.get_buckets()
counter = 0
for bucket in buckets:
    print "[%d] %s" % (counter,bucket.name)
    counter += 1

inp = int(raw_input('>>> Enter the bucket to mnt: '))
selection = buckets[inp].name
print 'you selected: %s' % selection
mountpt = raw_input('>>> please enter the mnt point: ')
print 'mounting %s at: %s' % (selection,mountpt)
os.system('s3fs %s -o accessKeyId=%s -o secretAccessKey=%s %s' % (selection,
                                                                  cfg.aws.get('AWS_ACCESS_KEY_ID'),
                                                                  cfg.aws.get('AWS_SECRET_ACCESS_KEY'),mountpt))
