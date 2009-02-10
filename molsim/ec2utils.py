#!/usr/bin/env python

""" 
EC2 Utils
"""

import os, sys, re, time, socket
from threading import Thread
import EC2
from spinner import Spinner
from ssh import ssh, scp

def ec2ssh():
    """ I don't believe this is necessary anymore...plus it's ugly as hell"""
    homedir = os.path.expanduser( '~' )
    id_rsa_location = homedir+'/.ssh/id_rsa'

    # Prep client machine: the following adds the Amazon getting started guide (gsg) private key in your client machine's id_rsa file for passwordless login to the master node,
    # you can replace this key with whatever you want, just make sure it matches what you used in your config file for launching the images.

    id_rsa_file = open(id_rsa_location,'r')
    key_file = open(KEY_LOCATION,'r')

    id_rsa_contents = id_rsa_file.read().replace('+','')
    key_contents = key_file.read().replace('+','')

    # done reading, reopen in case we need to append the key
    id_rsa_file.close()
    id_rsa_file = open(id_rsa_location,'a')

    regexp = re.compile(key_contents)

    if not regexp.search(id_rsa_contents):
        print '>>> ssh key is not in id_rsa.  adding it now...'
        # key not in id_rsa, add it
        key_file.seek(0)
        for line in key_file.readlines():
            id_rsa_file.writelines(line)
    else: 
        print '>>> ssh key in id_rsa file'

    id_rsa_file.close()
    key_file.close()

    # fix id_rsa permissions, regardless
    os.chmod(id_rsa_location,0600)

def is_cluster_up():
    running_instances = get_running_instances()
    if len(running_instances) == DEFAULT_CLUSTER_SIZE:
        return True
    else:
        return False

def get_instance_response():
    conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    instance_response=conn.describe_instances()
    parsed_response=instance_response.parse()  
    return parsed_response

def get_running_instances():
    parsed_response = get_instance_response() 
    running_instances=[]
    for chunk in parsed_response:
        #if chunk[0]=='INSTANCE' and chunk[-1]=='running':
        if chunk[0]=='INSTANCE' and chunk[5]=='running':
            if chunk[2] == IMAGE_ID or chunk[2] == MASTER_IMAGE_ID:
                running_instances.append(chunk[1])
    return running_instances

def create_mpd_hosts_file():
    # Configure mpd.hosts: write out the hostnames to a mpd.hosts file
    hosts_file= "mpd.hosts"
    output=open(hosts_file,'w')
    internal_hostnames = get_internal_hostnames()
    for host in internal_hostnames:
        print >> output, "%s" % host
    output.close()
    return hosts_file


def get_external_hostnames():
    parsed_response=get_instance_response() 
    if len(parsed_response) == 0:
        return None        
    external_hostnames = []
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

def list_instances():
    parsed_response = get_instance_response()
    if len(parsed_response) != 0:
        print ">>> EC2 Instances:"
        for instance in parsed_response:
            if instance[0] == 'INSTANCE':
                print ' '.join(instance)
    
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
            #if chunk[-1]=='running' or chunk[-1]=='pending':
            if chunk[5]=='running' or chunk[5]=='pending':
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

def ssh_to_master():
    master_node = get_master_node()
    if master_node is not None:
        print "\n>>> MASTER NODE: %s" % master_node
        ssh(master_node, credential=KEY_LOCATION)
    else: 
        print ">>> No master node found..."

def start_cluster():
    print ">>> Starting cluster..."
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

    master_node = get_master_node()
    print "\n>>> The master node is %s" % master_node

    print "\n>>> Writing out mpd.hosts file (MPI)"
    hosts_file = create_mpd_hosts_file()

    # upload the gsg private key (or whatever you named it) , copy over create_hosts.py, and execute the script all on the master node.  The script 
    # will then, using AWS internal network, setup passwordless ssh between the nodes as well as setup /etc/hosts, nfs, sge, mpi, etc
    scp(master_node, user=CLUSTER_USER, src=KEY_LOCATION, dest="~/.ssh/id_rsa", credential=KEY_LOCATION)
    scp(master_node, src=hosts_file, dest="/etc/", credential=KEY_LOCATION)

    print ">>> Creating hosts file on master node and copying hosts file to compute nodes..."
    scp(master_node, src="EC2config.py", dest="/home/", credential=KEY_LOCATION)
    scp(master_node, src="ssh.py", dest="/home/", credential=KEY_LOCATION)
    scp(master_node, src="create_hosts.py", dest="/home/", credential=KEY_LOCATION)
    ssh(master_node, cmd="python /home/create_hosts.py", credential=KEY_LOCATION)
        
    print "\n>>> The cluster has been started. ssh into the master node as %s by running:" % CLUSTER_USER
    print "$ ssh %s@%s " % (CLUSTER_USER,master_node)

def create_cluster():
    conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    if globals().has_key("MASTER_IMAGE_ID"):
        print ">>> Launching master node..."
        print ">>> MASTER AMI: ",MASTER_IMAGE_ID
        master_response = conn.run_instances(imageId=MASTER_IMAGE_ID, instanceType=INSTANCE_TYPE, minCount=1, maxCount=1, keyName= KEYNAME )
        print master_response

        print ">>> Launching worker nodes..."
        print ">>> NODE AMI: ",IMAGE_ID
        instances_response = conn.run_instances(imageId=IMAGE_ID, instanceType=INSTANCE_TYPE, minCount=max((DEFAULT_CLUSTER_SIZE-1)/2, 1), maxCount=max(DEFAULT_CLUSTER_SIZE-1,1), keyName= KEYNAME )
        print instances_response
        # if the workers failed, what should we do about the master?
    else:
        print ">>> Launching master and worker nodes..."
        print ">>> MASTER AMI: ",IMAGE_ID
        print ">>> NODE AMI: ",IMAGE_ID
        instances_response = conn.run_instances(imageId=IMAGE_ID, instanceType=INSTANCE_TYPE, minCount=max(DEFAULT_CLUSTER_SIZE/2,1), maxCount=max(DEFAULT_CLUSTER_SIZE,1), keyName= KEYNAME )
        # instances_response is a list: [["RESERVATION", reservationId, ownerId, ",".join(groups)],["INSTANCE", instanceId, imageId, dnsName, instanceState], [ "INSTANCE"etc])
        # same as "describe instance"
        print instances_response

def stop_cluster():
    resp = raw_input(">>> This will shutdown all EC2 instances. Are you sure (yes/no)? ")
    if resp == 'yes':
        print ">>>  Listing instances ..."
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


class Spinner(Thread):
    spin_screen_pos = 0     #Set the screen position of the spinner (chars from the left).
    char_index_pos = 0      #Set the current index position in the spinner character list.
    sleep_time = 1       #Set the time between character changes in the spinner.
    spin_type = 2          #Set the spinner type: 0-3

    def __init__(self, type=spin_type):
        Thread.__init__(self)
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
                break
            self.char_index_pos = self.Print(self.char_index_pos)

if __name__ == "__main__":
    s = Spinner()
    print 'Waiting for cluster...',
    s.start()
    time.sleep(3)
    s.stop = True
