#!/usr/bin/env python
from molsim.molsimcfg import *
from molsim import S3

def get_conn():
    return S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

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
    files = [ entry.key for entry in conn.list_bucket(bucket_name).entries] 
    return files

def show_bucket_files(bucket_name):
    files = get_bucket_files(bucket_name)
    for file in files:
        print file

def remove_file(bucket_name, file_name):
    conn = get_conn()
    conn.delete(bucket_name, file_name)

if __name__ == "__main__":
    print get_buckets()
