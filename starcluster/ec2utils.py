#!/usr/bin/env python

""" 
EC2 Utils
"""

import os
import re
import sys
import time
import socket
from threading import Thread

from starcluster import EC2

from starcluster.starclustercfg import *
from starcluster.s3utils import get_bucket_files, remove_file
from starcluster import cluster_setup
from ssh import Connection

def print_timing(func):
    def wrapper(*arg, **kargs):
        t1 = time.time()
        res = func(*arg, **kargs)
        t2 = time.time()
        print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
        return res
    return wrapper

def get_conn():
    return EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

def is_ssh_up():
    external_hostnames = get_external_hostnames()
    for ehost in external_hostnames:
        s = socket.socket()
        s.settimeout(0.25)
        try:
            s.connect((ehost, 22))
            s.close()
        except socket.error:
            return False
    return True

def is_cluster_up():
    running_instances = get_running_instances()
    if len(running_instances) == DEFAULT_CLUSTER_SIZE:
        if is_ssh_up():
            return True
        else:
            return False
    else:
        return False

def get_registered_images():
    conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    image_list = conn.describe_images(owners=["self"]).parse()
    images = {}
    for image in image_list:
        image_name = os.path.basename(image[2]).split('.manifest.xml')[0]
        images[image_name] = {}
        img_dict = images[image_name]
        img_dict['NAME'] = image_name
        img_dict['AMI'] = image[1]
        img_dict['MANIFEST'] = image[2] 
        img_dict['BUCKET'] = os.path.dirname(image[2])
        img_dict['STATUS'] = image[4] 
        img_dict['PRIVACY'] = image[5] 
    return images

def get_image(image_name):
    return get_registered_images()[image_name]

def list_registered_images():
    images = get_registered_images()
    for image in images.keys():
        print "%(NAME)s AMI=%(AMI)s BUCKET=%(BUCKET)s MANIFEST=%(MANIFEST)s" % images[image]

def remove_image_files(image_name, bucket = None, pretend=True):
    if not bucket:
        bucket = get_image(image_name)['BUCKET']
    files = get_image_files(image_name, bucket)
    for file in files:
        if pretend:
            print file
        else:
            print 'removing file %s' % file
            remove_file(bucket, file)

    # recursive double check
    files = get_image_files(image_name, bucket)
    if len(files) != 0:
        if pretend:
            print 'not all files deleted, would recurse'
        else:
            print 'not all files deleted, recursing'
            remove_image_files(image_name, bucket, pretend)
    

def remove_image(image_name, pretend=True):
    # first remove image files
    remove_image_files(image_name, pretend = pretend)

    # then deregister ami
    image = get_image(image_name)
    print 'removing %s (ami: %s)' % (image['NAME'],image['AMI'])
    if pretend:
        print 'would run conn.deregister_image()'
    else:
        conn = get_conn()
        conn.deregister_image(image['AMI'])

def list_image_files(image_name, bucket=None):
    files = get_image_files(image_name, bucket)
    for file in files:
        print file

def get_image_files(image_name, bucket=None):
    if bucket:
        bucket_files = get_bucket_files(bucket)
    else:
        image = get_image(image_name)
        bucket_files = get_bucket_files(image['BUCKET'])
    image_files = []
    for file in bucket_files:
        if file.split('.part.')[0] == image_name:
            image_files.append(file)
    return image_files

def get_instance_response():
    conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    instance_response=conn.describe_instances()
    parsed_response=instance_response.parse()  
    return parsed_response

def get_running_instances(strict=True):
    parsed_response = get_instance_response() 
    running_instances=[]
    for chunk in parsed_response:
        if chunk[0]=='INSTANCE' and chunk[5]=='running':
            if strict:
                if chunk[2] == IMAGE_ID or chunk[2] == MASTER_IMAGE_ID:
                    running_instances.append(chunk[1])
            else:
                running_instances.append(chunk[1])
    return running_instances

def get_external_hostnames():
    parsed_response=get_instance_response() 
    external_hostnames = []
    if len(parsed_response) == 0:
        return external_hostnames        
    for chunk in parsed_response:
        #if chunk[0]=='INSTANCE' and chunk[-1]=='running':
        if chunk[0]=='INSTANCE' and chunk[5]=='running':
            external_hostnames.append(chunk[3])
    return external_hostnames

def get_internal_hostnames():
    parsed_response=get_instance_response() 
    if len(parsed_response) == 0:
        return None
    internal_hostnames = []    
    for chunk in parsed_response:
        #if chunk[0]=='INSTANCE' and chunk[-1]=='running' :
        if chunk[0]=='INSTANCE' and chunk[5]=='running' :
            internal_hostnames.append(chunk[4])
    return internal_hostnames

def get_instances():
    parsed_response = get_instance_response()
    instances = []
    if len(parsed_response) != 0:
        for instance in parsed_response:
            if instance[0] == 'INSTANCE':
                instances.append(instance)
    return instances

def list_instances():
    instances = get_instances()
    if len(instances) != 0:
        counter = 0
        print ">>> EC2 Instances:"
        for instance in instances:
            print "[%s] %s %s (%s)" % (counter, instance[3], instance[5],instance[2])
            counter +=1
    else:
        print ">>> No instances found..."
    
def terminate_instances(instances=None):
    if instances is not None:
        conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        conn.terminate_instances(instances)

def get_master_node():
    parsed_response=get_instance_response() 
    if len(parsed_response) == 0:
        return None
    instances=[]
    hostnames=[]
    externalnames=[]
    machine_state=[]
    for chunk in parsed_response:
        if chunk[0]=='INSTANCE':
            #if chunk[5]=='running' or chunk[5]=='pending':
            if chunk[5]=='running':
                instances.append(chunk[1])
                hostnames.append(chunk[4])
                externalnames.append(chunk[3])              
                #machine_state.append(chunk[-1])
                machine_state.append(chunk[5])
    try:
        master_node  = externalnames[0]
    except:
        master_node = None
    return master_node

def get_master_instance():
    instances = get_running_instances()
    try:
        master_instance = instances[0] 
    except:
        master_instance = None
    return master_instance

def ssh_to_master():
    master_node = get_master_node()
    if master_node is not None:
        print "\n>>> MASTER NODE: %s" % master_node
        os.system('ssh -i %s root@%s' % (KEY_LOCATION, master_node)) 
    else: 
        print ">>> No master node found..."

def ssh_to_node(node_number):
    nodes = get_external_hostnames()
    if len(nodes) == 0:
        print '>>> No instances to connect to...exiting'
        return

    try:
        node = nodes[int(node_number)]
        print ">>> Logging into node: %s" % node
        os.system('ssh -i %s root@%s' % (KEY_LOCATION, node))
    except:
        print ">>> Invalid node_number. Please select a node number from the output of manage-cluster.py -l"

def get_nodes():
    internal_hostnames = get_internal_hostnames()
    external_hostnames = get_external_hostnames()
    
    nodes = []
    nodeid = 0
    for ihost, ehost in  zip(internal_hostnames,external_hostnames):
        node = {}
        print '>>> Creating persistent connection to %s' % ehost
        node['CONNECTION'] = Connection(ehost, username='root', private_key=KEY_LOCATION)
        node['NODE_ID'] = nodeid
        node['EXTERNAL_NAME'] = ehost
        node['INTERNAL_NAME'] = ihost
        node['INTERNAL_IP'] = node['CONNECTION'].execute('python -c "import socket; print socket.gethostbyname(\'%s\')"' % ihost)[0].strip()
        node['INTERNAL_NAME_SHORT'] = ihost.split('.')[0]
        if nodeid == 0:
            node['INTERNAL_ALIAS'] = 'master'
        else:
            node['INTERNAL_ALIAS'] = 'node%.3d' % nodeid
        nodes.append(node)
        nodeid += 1
    return nodes

@print_timing
def start_cluster(create=True):
    print ">>> Starting cluster..."
    if create:
        create_cluster()
    s = Spinner()
    print ">>> Waiting for cluster to start...",
    s.start()
    while True:
        if is_cluster_up():
            s.stop = True
            break
        else:  
            time.sleep(15)

    attach_volume_to_master()

    master_node = get_master_node()
    print ">>> The master node is %s" % master_node

    print ">>> Setting up the cluster..."
    cluster_setup.main(get_nodes())
        
    print "\n>>> The cluster has been started and configured. ssh into the master node as root by running:" 
    print ""
    print "$ manage-cluster.py -m"
    print ""
    print ">>> or as %s directly:" % CLUSTER_USER
    print ""
    print "$ ssh -i %s %s@%s " % (KEY_LOCATION, CLUSTER_USER, master_node)
    print ""

def create_cluster():
    conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    if globals().has_key("MASTER_IMAGE_ID"):
        print ">>> Launching master node..."
        print ">>> MASTER AMI: ",MASTER_IMAGE_ID
        master_response = conn.run_instances(imageId=MASTER_IMAGE_ID, instanceType=INSTANCE_TYPE, minCount=1, maxCount=1, keyName= KEYNAME, availabilityZone = AVAILABILITY_ZONE)
        print master_response

        print ">>> Launching worker nodes..."
        print ">>> NODE AMI: ",IMAGE_ID
        instances_response = conn.run_instances(imageId=IMAGE_ID, instanceType=INSTANCE_TYPE, minCount=max((DEFAULT_CLUSTER_SIZE-1)/2, 1), maxCount=max(DEFAULT_CLUSTER_SIZE-1,1), keyName= KEYNAME, availabilityZone = AVAILABILITY_ZONE)
        print instances_response
        # if the workers failed, what should we do about the master?
    else:
        print ">>> Launching master and worker nodes..."
        print ">>> MASTER AMI: ",IMAGE_ID
        print ">>> NODE AMI: ",IMAGE_ID
        instances_response = conn.run_instances(imageId=IMAGE_ID, instanceType=INSTANCE_TYPE, minCount=max(DEFAULT_CLUSTER_SIZE/2,1), maxCount=max(DEFAULT_CLUSTER_SIZE,1), keyName= KEYNAME ,availabilityZone = AVAILABILITY_ZONE)
        # instances_response is a list: [["RESERVATION", reservationId, ownerId, ",".join(groups)],["INSTANCE", instanceId, imageId, dnsName, instanceState], [ "INSTANCE"etc])
        # same as "describe instance"
        print instances_response

def stop_cluster():
    resp = raw_input(">>> This will shutdown all EC2 instances. Are you sure (yes/no)? ")
    if resp == 'yes':
        detach_volume()
        print ">>> Listing instances ..."
        list_instances()
        running_instances = get_running_instances()
        if len(running_instances) > 0:
            for instance in running_instances:
                print ">>> Shutting down instance: %s " % instance
            print "\n>>> Waiting for instances to shutdown ...."
            terminate_instances(running_instances)
            time.sleep(5)
        print ">>> Listing new state of instances" 
        list_instances()
    else:
        print ">>> Exiting without shutting down instances...."

def stop_slaves():
    print ">>> Listing instances ..."
    list_instances()
    running_instances = get_running_instances()
    if len(running_instances) > 0:
        #exclude master node....
        running_instances=running_instances[1:len(running_instances)]
        for instance in running_instances:
            print ">>> Shuttin down slave instance: %s " % instance
        print "\n>>> Waiting for shutdown ...."
        terminate_instances(running_instances)
        time.sleep(5)
    print ">>> Listing new state of slave instances"
    print list_instances()

def has_attach_volume():
    if globals().has_key("ATTACH_VOLUME") and globals()["ATTACH_VOLUME"] is not None:
        if globals().has_key("VOLUME_DEVICE") and globals()["VOLUME_DEVICE"] is not None:
            return True
        else:
            print ">>> No VOLUME_DEVICE specified in config"
    else:
        print ">>> No ATTACH_VOLUME specified in config"
    return False
        

def attach_volume_to_node(node):
    if has_attach_volume():
        conn = get_conn()
        return conn.attach_volume(ATTACH_VOLUME, node, VOLUME_DEVICE).parse()

def get_volumes():
    if has_attach_volume():
        conn = get_conn()
        return conn.describe_volumes([ATTACH_VOLUME]).parse()

def list_volumes():
    vols = get_volumes()
    if vols is not None:
        for vol in vols:
            print vol

def detach_volume():
    if has_attach_volume():
        print ">>> Detaching EBS device..."
        conn = get_conn()
        return conn.detach_volume(ATTACH_VOLUME).parse()
    else:
        print ">>> No EBS device to detach"

def attach_volume_to_master():
    print ">>> Attaching volume to master node..."
    master_instance = get_master_instance()
    if master_instance is not None:
        if attach_volume_to_node(master_instance) is not None:
            while True:
                vol = get_volumes()[0]
                if vol[0] == 'VOLUME':
                    if vol[1] == ATTACH_VOLUME and vol[4] == 'in-use':
                        return True
                    else:
                        time.sleep(5)
                        continue
                else:
                    return False

class Spinner(Thread):
    spin_screen_pos = 0     #Set the screen position of the spinner (chars from the left).
    char_index_pos = 0      #Set the current index position in the spinner character list.
    sleep_time = 1       #Set the time between character changes in the spinner.
    spin_type = 2          #Set the spinner type: 0-3

    def __init__(self, type=spin_type):
        Thread.__init__(self)
        self.setDaemon(True)
        self.stop = False
        if type == 0:
            self.char = ['O', 'o', '-', 'o','0']
        elif type == 1:
            self.char = ['.', 'o', 'O', 'o','.']
        elif type == 2:
            self.char = ['|', '/', '-', '\\', '-']
        else:
            self.char = ['*','#','@','%','+']
            self.len  = len(self.char)

    def Print(self,crnt):
        str, crnt = self.curr(crnt)
        sys.stdout.write("\b \b%s" % str)
        sys.stdout.flush() #Flush stdout to get output before sleeping!
        time.sleep(self.sleep_time)
        return crnt

    def curr(self,crnt): #Iterator for the character list position
        if crnt == 4:
            return self.char[4], 0
        elif crnt == 0:
            return self.char[0], 1
        else:
            test = crnt
            crnt += 1
        return self.char[test], crnt

    def done(self):
        sys.stdout.write("\b \b")
    
    def run(self):
        print " " * self.spin_screen_pos, #the comma keeps print from ending with a newline.
        while True:
            if self.stop:
                self.done()
                return
            self.char_index_pos = self.Print(self.char_index_pos)

if __name__ == "__main__":
    s = Spinner()
    print 'Waiting for cluster...',
    s.start()
    time.sleep(3)
    s.stop = True
