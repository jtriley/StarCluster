#!/usr/bin/env python

""" 
EC2 Utils
"""

import os
import sys
import time
import socket
import platform
from threading import Thread

from starcluster import EC2
from starcluster import starclustercfg as cfg
from starcluster import s3utils
from starcluster import cluster_setup
from starcluster import ssh
from starcluster.logger import log


def print_timing(func):
    def wrapper(*arg, **kargs):
        t1 = time.time()
        res = func(*arg, **kargs)
        t2 = time.time()
        log.info('%s took %0.3f mins' % (func.func_name, (t2-t1)/60.0))
        return res
    return wrapper

EC2_CONNECTION = None

def get_conn():
    if EC2_CONNECTION is None:
        log.debug('EC2_CONNECTION is None, creating...')
        globals()['EC2_CONNECTION'] = EC2.AWSAuthConnection(cfg.AWS_ACCESS_KEY_ID, cfg.AWS_SECRET_ACCESS_KEY)
    return EC2_CONNECTION

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
    if len(running_instances) == cfg.CLUSTER_SIZE:
        if is_ssh_up():
            return True
        else:
            return False
    else:
        return False

def get_registered_images():
    conn = get_conn()
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
    try:
        log.debug("attempting to fetch ami: %s" % image_name)
        return get_registered_images()[image_name]
    except:
        if image_name.startswith('ami') and len(image_name) == 12:
            for ami in get_registered_images().itervalues():
                if ami['AMI'] == image_name:
                    log.debug("returning ami: %s" % ami['AMI'])
                    return ami
        log.error("invalid AMI name/id specified: %s" % image_name)

def list_registered_images():
    images = get_registered_images()
    for image in images.keys():
        print "%(NAME)s AMI=%(AMI)s BUCKET=%(BUCKET)s MANIFEST=%(MANIFEST)s" % images[image]

def remove_image_files(image_name, bucket = None, pretend=True):
    image = get_image(image_name)
    if image is None:
        log.error('cannot remove AMI %s' % image_name)
        return
    bucket = image['BUCKET']
    files = get_image_files(image_name, bucket)
    for file in files:
        if pretend:
            print file
        else:
            print 'removing file %s' % file
            s3utils.remove_file(bucket, file)

    # recursive double check
    files = get_image_files(image_name, bucket)
    if len(files) != 0:
        if pretend:
            log.debug('not all files deleted, would recurse')
        else:
            log.debug('not all files deleted, recursing')
            remove_image_files(image_name, bucket, pretend)
    

def remove_image(image_name, pretend=True):
    image = get_image(image_name)
    if image is None:
        log.error('cannot remove AMI %s' % image_name)
        return

    # first remove image files
    remove_image_files(image_name, pretend = pretend)

    # then deregister ami
    if pretend:
        log.info('Would run conn.deregister_image for image %s (ami: %s)' % (image['NAME'],image['AMI']))
    else:
        log.info('Removing image %s (ami: %s)' % (image['NAME'],image['AMI']))
        conn = get_conn()
        conn.deregister_image(image['AMI'])

def list_image_files(image_name, bucket=None):
    files = get_image_files(image_name, bucket)
    for file in files:
        print file

def get_image_files(image_name, bucket=None):
    image = get_image(image_name)
    if image is not None:
        # recreating image_name in case they passed ami id instead of human readable
        image_name = image['NAME']
        bucket_files = s3utils.get_bucket_files(image['BUCKET'])
        image_files = []
        for file in bucket_files:
            if file.split('.part.')[0] == image_name:
                image_files.append(file)
        return image_files
    else:
        return []

INSTANCE_RESPONSE = None

def get_instance_response(refresh=False):
    if INSTANCE_RESPONSE is None or refresh:
        log.debug('INSTANCE_RESPONSE = %s, refresh = %s, creating' % (INSTANCE_RESPONSE, refresh))
        conn = get_conn()
        instance_response=conn.describe_instances()
        globals()['INSTANCE_RESPONSE'] = instance_response.parse()  
    return INSTANCE_RESPONSE
        
KEYPAIR_RESPONSE = None

def get_keypair_response(refresh=False):
    if KEYPAIR_RESPONSE is None or refresh:
        log.debug('KEYPAIR_RESPONSE = %s, refresh = %s, creating' % (KEYPAIR_RESPONSE, refresh))
        conn = get_conn()
        keypair_response = conn.describe_keypairs()
        globals()['KEYPAIR_RESPONSE'] = keypair_response.parse()
    return KEYPAIR_RESPONSE

def get_running_instances(refresh=True, strict=True):
    parsed_response = get_instance_response(refresh) 
    running_instances=[]
    for chunk in parsed_response:
        if chunk[0]=='INSTANCE' and chunk[5]=='running':
            if strict:
                if chunk[2] == cfg.NODE_IMAGE_ID or chunk[2] == cfg.MASTER_IMAGE_ID:
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
    internal_hostnames = []
    if len(parsed_response) == 0:
        return internal_hostnames
    for chunk in parsed_response:
        #if chunk[0]=='INSTANCE' and chunk[-1]=='running' :
        if chunk[0]=='INSTANCE' and chunk[5]=='running' :
            internal_hostnames.append(chunk[4])
    return internal_hostnames

def get_instances(refresh=False):
    parsed_response = get_instance_response(refresh)
    instances = []
    if len(parsed_response) != 0:
        for instance in parsed_response:
            if instance[0] == 'INSTANCE':
                instances.append(instance)
    return instances

def list_instances(refresh=False):
    instances = get_instances(refresh)
    if len(instances) != 0:
        counter = 0
        log.info("EC2 Instances:")
        for instance in instances:
            print "[%s] %s %s (%s)" % (counter, instance[3], instance[5],instance[2])
            counter +=1
    else:
        log.info("No instances found...")
    
def terminate_instances(instances=None):
    if instances is not None:
        conn = get_conn()
        conn.terminate_instances(instances)

def get_master_node():
    external_hostnames = get_external_hostnames()
    try:
        return external_hostnames[0]
    except Exception,e:
        return None
        
def get_master_instance():
    instances = get_running_instances()
    try:
        master_instance = instances[0] 
    except Exception,e:
        master_instance = None
    return master_instance

def ssh_to_master():
    master_node = get_master_node()
    if master_node is not None:
        log.info("MASTER NODE: %s" % master_node)
        if platform.system() != 'Windows':
            os.system('ssh -i %s root@%s' % (cfg.KEY_LOCATION, master_node)) 
        else:
            os.system('putty -ssh -i %s root@%s' % (cfg.KEY_LOCATION, master_node))
    else: 
        log.info("No master node found...")

def ssh_to_node(node_number):
    nodes = get_external_hostnames()
    if len(nodes) == 0:
        log.info('No instances to connect to...exiting')
        return
    try:
        node = nodes[int(node_number)]
        log.info("Logging into node: %s" % node)
        if platform.system() != 'Windows':
            os.system('ssh -i %s root@%s' % (cfg.KEY_LOCATION, node))
        else:
            os.system('putty -ssh -i %s root@%s' % (cfg.KEY_LOCATION, node))
    except:
        log.error("Invalid node_number. Please select a node number from the output of starcluster -l")

def get_nodes():
    internal_hostnames = get_internal_hostnames()
    external_hostnames = get_external_hostnames()

    nodes = []
    nodeid = 0
    for ihost, ehost in zip(internal_hostnames,external_hostnames):
        node = {}
        log.debug('Creating persistent connection to %s' % ehost)
        node['CONNECTION'] = ssh.Connection(ehost, username='root', private_key=cfg.KEY_LOCATION)
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
    log.info("Starting cluster...")
    if create:
        create_cluster()
    s = Spinner()
    log.log(logger.INFO_NO_NEWLINE, "Waiting for cluster to start...")
    s.start()
    while True:
        if is_cluster_up():
            s.stop()
            break
        else:  
            time.sleep(15)

    if has_attach_volume():
        attach_volume_to_master()

    master_node = get_master_node()
    log.info("The master node is %s" % master_node)

    log.info("Setting up the cluster...")
    cluster_setup.main(get_nodes())
        
    log.info("""

The cluster has been started and configured. ssh into the master node as root by running: 

$ starcluster -m

or as %(user)s directly:

$ ssh -i %(key)s %(user)s@%(master)s

""" % {'master': master_node, 'user': cfg.CLUSTER_USER, 'key': cfg.KEY_LOCATION}
    )

def create_cluster():
    conn = get_conn()

    log.info("Launching a %d-node cluster..." % cfg.CLUSTER_SIZE)

    if cfg.MASTER_IMAGE_ID is None:
        cfg.MASTER_IMAGE_ID = cfg.NODE_IMAGE_ID

    log.info("Launching master node...")
    log.info("MASTER AMI: %s" % cfg.MASTER_IMAGE_ID)
    master_response = conn.run_instances(imageId=cfg.MASTER_IMAGE_ID, instanceType=cfg.INSTANCE_TYPE, \
                                         minCount=1, maxCount=1, keyName=cfg.KEYNAME, availabilityZone=cfg.AVAILABILITY_ZONE)
    print master_response
    
    if cfg.CLUSTER_SIZE > 1:
        log.info("Launching worker nodes...")
        log.info("NODE AMI: %s" % cfg.NODE_IMAGE_ID)
        instances_response = conn.run_instances(imageId=cfg.NODE_IMAGE_ID, instanceType=cfg.INSTANCE_TYPE, \
                                                minCount=max((cfg.CLUSTER_SIZE-1)/2, 1), maxCount=max(cfg.CLUSTER_SIZE-1,1), \
                                                keyName=cfg.KEYNAME, availabilityZone=cfg.AVAILABILITY_ZONE)
        print instances_response
        # if the workers failed, what should we do about the master?

def stop_cluster():
    resp = raw_input(">>> This will shutdown all EC2 instances. Are you sure (yes/no)? ")
    if resp == 'yes':
        running_instances = get_running_instances()
        if len(running_instances) > 0:
            if has_attach_volume():
                detach_vol = detach_volume()
                log.debug("detach_vol_response: \n%s" % detach_vol)
            log.info("Listing instances ...")
            list_instances()
            for instance in running_instances:
                log.info("Shutting down instance: %s " % instance)
            log.info("Waiting for instances to shutdown ....")
            terminate_instances(running_instances)
            time.sleep(5)
            log.info("Listing new state of instances")
            list_instances(refresh=True)
        else:
            log.info('No running instances found, exiting...')
    else:
        log.info("Exiting without shutting down instances....")

def stop_slaves():
    running_instances = get_running_instances()
    if len(running_instances) > 0:
        log.info("Listing instances...")
        list_instances(refresh=True)
        #exclude master node....
        running_instances=running_instances[1:len(running_instances)]
        for instance in running_instances:
            log.info("Shutting down slave instance: %s " % instance)
        log.info("Waiting for shutdown...")
        terminate_instances(running_instances)
        time.sleep(5)
        log.info("Listing new state of slave instances")
        list_instances(refresh=True)
    else:
        log.info("No running instances found, exiting...")

def has_attach_volume():
    if cfg.ATTACH_VOLUME is not None:
        if cfg.VOLUME_DEVICE is not None:
            return True
        else:
            log.debug("No VOLUME_DEVICE specified in config")
    else:
        log.debug("No ATTACH_VOLUME specified in config")
    return False

def attach_volume_to_node(node):
    if has_attach_volume():
        conn = get_conn()
        return conn.attach_volume(cfg.ATTACH_VOLUME, node, cfg.VOLUME_DEVICE).parse()

def get_volumes():
    conn = get_conn()
    return conn.describe_volumes().parse()

def get_attach_volume():
    if has_attach_volume():
        conn = get_conn()
        return conn.describe_volumes([cfg.ATTACH_VOLUME]).parse()

def list_volumes():
    vols = get_volumes()
    if vols is not None:
        for vol in vols:
            print vol

def detach_volume():
    if has_attach_volume():
        log.info("Detaching EBS device...")
        conn = get_conn()
        return conn.detach_volume(cfg.ATTACH_VOLUME).parse()
    else:
        log.info("No EBS device to detach")

def attach_volume_to_master():
    log.info("Attaching volume to master node...")
    master_instance = get_master_instance()
    if master_instance is not None:
        attach_response = attach_volume_to_node(master_instance)
        log.debug("attach_response = %s" % attach_response)
        if attach_response is not None:
            while True:
                attach_volume = get_attach_volume()
                if len(attach_volume) != 2:
                    time.sleep(5)
                    continue
                vol = attach_volume[0]
                attachment = attach_volume[1]
                if vol[0] != 'VOLUME' or attachment[0] != 'ATTACHMENT':
                    return False
                if vol[1] != attachment[1] != cfg.ATTACH_VOLUME:
                    return False
                if vol[4] == "in-use" and attachment[5] == "attached":
                    return True
                time.sleep(5)

class Spinner(Thread):
    spin_screen_pos = 1     #Set the screen position of the spinner (chars from the left).
    char_index_pos = 0      #Set the current index position in the spinner character list.
    sleep_time = 1       #Set the time between character changes in the spinner.
    spin_type = 2          #Set the spinner type: 0-3

    def __init__(self, type=spin_type):
        Thread.__init__(self)
        self.setDaemon(True)
        self.stop_spinner = False
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
        sys.stdout.write("\b \b\n")

    def stop(self):
        self.stop_spinner = True
        time.sleep(0.5) #give time for run to get the message
    
    def run(self):
        print " " * self.spin_screen_pos, #the comma keeps print from ending with a newline.
        while True:
            if self.stop_spinner:
                self.done()
                return
            self.char_index_pos = self.Print(self.char_index_pos)

if __name__ == "__main__":
    # test the spinner
    s = Spinner()
    print 'Waiting for process...',
    s.start()
    time.sleep(3)
    s.stop()
    print 'Process is finished...'
