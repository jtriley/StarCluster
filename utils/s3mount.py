#!/usr/bin/env python
import os

from molsim import S3
from molsim.molsimcfg import *

print 'Simple wrapper script for s3fs (http://s3fs.googlecode.com/)'

conn = S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
buckets = conn.list_all_my_buckets()

counter = 0
for bucket in buckets.entries:
    print "[%d] %s" % (counter,bucket.name)
    counter += 1

inp = int(raw_input('>>> Enter the bucket to mnt: '))
selection = buckets.entries[inp].name
print 'you selected: %s' % selection
mountpt = raw_input('>>> please enter the mnt point: ')
print 'mounting %s at: %s' % (selection,mountpt)
os.system('s3fs %s -o accessKeyId=%s -o secretAccessKey=%s %s' % (selection,AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,mountpt))
