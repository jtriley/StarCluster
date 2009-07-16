#!/usr/bin/env python
import logging
import starcluster.starclustercfg as cfg
from starcluster import S3

log = logging.getLogger('starcluster')

S3_CONNECTION = None

def get_conn():
    if S3_CONNECTION is None:
        log.debug('S3_CONNECTION is None, creating...')
        globals()['S3_CONNECTION'] = S3.AWSAuthConnection(cfg.AWS_ACCESS_KEY_ID, cfg.AWS_SECRET_ACCESS_KEY)
    return S3_CONNECTION

def bucket_exists(bucket_name):
    exists = (get_conn().check_bucket_exists(bucket_name).reason == 'OK')
    log.error('bucket %s does not exist' % bucket_name)
    return exists

def get_buckets():
    conn = get_conn()
    bucket_list = conn.list_all_my_buckets().entries
    buckets = []
    for bucket in bucket_list:
        buckets.append(bucket.name)
    return buckets

def list_buckets():
    for bucket in get_buckets():
        print bucket

def get_bucket_files(bucket_name):
    conn = get_conn()
    if bucket_exists(bucket_name):
        files = [ entry.key for entry in conn.list_bucket(bucket_name).entries] 
    else:
        files = []
    return files

def show_bucket_files(bucket_name):
    if bucket_exists(bucket_name):
        files = get_bucket_files(bucket_name)
        for file in files:
            print file

def remove_file(bucket_name, file_name):
    conn = get_conn()
    conn.delete(bucket_name, file_name)

if __name__ == "__main__":
    print get_buckets()
