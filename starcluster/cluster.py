#!/usr/bin/env python
import os
import socket
import ssh
import cluster_setup
from spinner import Spinner
from utils import AttributeDict, print_timing
from static import INSTANCE_TYPES
from logger import log

def get_cluster(**kwargs):
    """Factory for Cluster class"""
    return Cluster(**kwargs)

class Cluster(AttributeDict):
    def __init__(self,
            CLUSTER_SIZE=None,
            CLUSTER_USER=None,
            CLUSTER_SHELL=None,
            MASTER_IMAGE_ID=None,
            NODE_IMAGE_ID=None,
            INSTANCE_TYPE=None,
            AVAILABILITY_ZONE=None,
            KEYNAME=None,
            KEY_LOCATION=None,
            ATTACH_VOLUME=None,
            VOLUME_DEVICE=None,
            VOLUME_PARTITION=None,
            **kwargs):
        self.update({
            'CLUSTER_SIZE':CLUSTER_SIZE,
            'CLUSTER_USER':CLUSTER_USER,
            'CLUSTER_SHELL':CLUSTER_SHELL,
            'MASTER_IMAGE_ID':MASTER_IMAGE_ID,
            'NODE_IMAGE_ID':NODE_IMAGE_ID,
            'INSTANCE_TYPE':INSTANCE_TYPE,
            'AVAILABILITY_ZONE':AVAILABILITY_ZONE,
            'KEYNAME':KEYNAME,
            'KEY_LOCATION':KEY_LOCATION,
            'ATTACH_VOLUME':ATTACH_VOLUME,
            'VOLUME_DEVICE':VOLUME_DEVICE,
            'VOLUME_PARTITION':VOLUME_PARTITION,
        })

    def create_cluster(self):
        log.info("Launching a %d-node cluster..." % self.CLUSTER_SIZE)

        if self.MASTER_IMAGE_ID is None:
            self.MASTER_IMAGE_ID = self.NODE_IMAGE_ID

        log.info("Launching master node...")
        log.info("MASTER AMI: %s" % self.MASTER_IMAGE_ID)
        master_response = conn.run_instances(imageId=self.MASTER_IMAGE_ID,
            instanceType=self.INSTANCE_TYPE,
            minCount=1, maxCount=1,
            keyName=self.KEYNAME,
            availabilityZone=self.AVAILABILITY_ZONE)
        print master_response
        
        if self.CLUSTER_SIZE > 1:
            log.info("Launching worker nodes...")
            log.info("NODE AMI: %s" % self.NODE_IMAGE_ID)
            instances_response = conn.run_instances(imageId=self.NODE_IMAGE_ID,
                instanceType=self.INSTANCE_TYPE,
                minCount=max((self.CLUSTER_SIZE-1)/2, 1),
                maxCount=max(self.CLUSTER_SIZE-1,1),
                keyName=self.KEYNAME,
                availabilityZone=self.AVAILABILITY_ZONE)
            print instances_response

    def is_ssh_up(self):
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

    def is_cluster_up(self):
        running_instances = get_running_instances()
        if len(running_instances) == self.CLUSTER_SIZE:
            if is_ssh_up():
                return True
            else:
                return False
        else:
            return False

    def attach_volume_to_master(self):
        log.info("Attaching volume to master node...")
        master_instance = get_master_instance()
        if master_instance is not None:
            attach_response = attach_volume_to_node(master_instance)
            log.debug("attach_response = %s" % attach_response)
            if attach_response is not None:
                while True:
                    attach_volume = get_volume()
                    if len(attach_volume) != 2:
                        time.sleep(5)
                        continue
                    vol = attach_volume[0]
                    attachment = attach_volume[1]
                    if vol[0] != 'VOLUME' or attachment[0] != 'ATTACHMENT':
                        return False
                    if vol[1] != attachment[1] != self.ATTACH_VOLUME:
                        return False
                    if vol[4] == "in-use" and attachment[5] == "attached":
                        return True
                    time.sleep(5)

    def get_nodes(self):
        internal_hostnames = get_internal_hostnames()
        external_hostnames = get_external_hostnames()

        nodes = []
        nodeid = 0
        for ihost, ehost in zip(internal_hostnames,external_hostnames):
            node = {}
            log.debug('Creating persistent connection to %s' % ehost)
            node['CONNECTION'] = ssh.Connection(ehost, username='root',
            private_key=self.KEY_LOCATION)
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

    def ssh_to_node(self,node_number):
        nodes = get_external_hostnames()
        if len(nodes) == 0:
            log.info('No instances to connect to...exiting')
            return
        try:
            node = nodes[int(node_number)]
            log.info("Logging into node: %s" % node)
            if platform.system() != 'Windows':
                os.system('ssh -i %s root@%s' % (self.KEY_LOCATION, node))
            else:
                os.system('putty -ssh -i %s root@%s' % (self.KEY_LOCATION, node))
        except:
            log.error("Invalid node_number. Please select a node number from the output of starcluster -l")

    def ssh_to_master(self):
        master_node = get_master_node()
        if master_node is not None:
            log.info("MASTER NODE: %s" % master_node)
            if platform.system() != 'Windows':
                os.system('ssh -i %s root@%s' % (self.KEY_LOCATION, master_node)) 
            else:
                os.system('putty -ssh -i %s root@%s' % (self.KEY_LOCATION, master_node))
        else: 
            log.info("No master node found...")

    def get_master_node(self):
        external_hostnames = get_external_hostnames()
        try:
            return external_hostnames[0]
        except Exception,e:
            return None
            
    def get_master_instance(self):
        instances = get_running_instances()
        try:
            master_instance = instances[0] 
        except Exception,e:
            master_instance = None
        return master_instance


    def stop_cluster(self):
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

    def stop_slaves(self):
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

    @print_timing
    def start_cluster(self, create=True):
        log.info("Starting cluster...")
        if create:
            create_cluster()
        s = Spinner()
        log.log(logger.INFO_NO_NEWLINE, "Waiting for cluster to start...")
        s.start()
        while True:
            if self.is_cluster_up():
                s.stop()
                break
            else:  
                time.sleep(15)

        if self.has_attach_volume():
            self.attach_volume_to_master()

        master_node = self.get_master_node()
        log.info("The master node is %s" % master_node)

        log.info("Setting up the cluster...")
        cluster_setup.main(self.get_nodes())
            
        log.info("""

The cluster has been started and configured. ssh into the master node as root by running: 

$ starcluster sshmaster 

or as %(user)s directly:

$ ssh -i %(key)s %(user)s@%(master)s

        """ % {'master': master_node, 'user': self.CLUSTER_USER, 'key': self.KEY_LOCATION})

    def is_valid(self, cluster): 
        CLUSTER_SIZE = cluster.CLUSTER_SIZE
        KEYNAME = cluster.KEYNAME
        KEY_LOCATION = cluster.KEY_LOCATION
        conn = self.conn 
        if not self._has_all_required_settings(cluster):
            log.error('Please specify the required settings in %s' % CFG_FILE)
            return False
        if not self._has_valid_credentials():
            log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
            return False
        if not self._has_keypair(cluster):
            log.error('Account does not contain a key with KEYNAME = %s. Please check your settings' % KEYNAME)
            return False
        if not os.path.exists(KEY_LOCATION):
            log.error('KEY_LOCATION=%s does not exist. Please check your settings' % KEY_LOCATION)
            return False
        elif not os.path.isfile(KEY_LOCATION):
            log.error('KEY_LOCATION=%s is not a file. Please check your settings' % KEY_LOCATION)
            return False
        if CLUSTER_SIZE <= 0:
            log.error('CLUSTER_SIZE must be a positive integer. Please check your settings')
            return False
        if not self._has_valid_availability_zone(cluster):
            log.error('Your AVAILABILITY_ZONE setting is invalid. Please check your settings')
            return False
        if not self._has_valid_ebs_settings(cluster):
            log.error('EBS settings are invalid. Please check your settings')
            return False
        if not self._has_valid_image_settings(cluster):
            log.error('Your MASTER_IMAGE_ID/NODE_IMAGE_ID setting(s) are invalid. Please check your settings')
            return False
        if not self._has_valid_instance_type_settings(cluster):
            log.error('Your INSTANCE_TYPE setting is invalid. Please check your settings')
            return False
        return True


    def _has_valid_image_settings(self, cluster):
        MASTER_IMAGE_ID = cluster.MASTER_IMAGE_ID
        NODE_IMAGE_ID = cluster.NODE_IMAGE_ID
        conn = self.conn
        image = conn.describe_images(imageIds=[NODE_IMAGE_ID]).parse()
        if not image:
            log.error('NODE_IMAGE_ID %s does not exist' % NODE_IMAGE_ID)
            return False
        if MASTER_IMAGE_ID is not None:
            master_image = conn.describe_images(imageIds=[MASTER_IMAGE_ID]).parse()
            if not master_image:
                log.error('MASTER_IMAGE_ID %s does not exist' % MASTER_IMAGE_ID)
                return False
        return True

    def _has_valid_availability_zone(self, cluster):
        conn = self.conn
        AVAILABILITY_ZONE = cluster.AVAILABILITY_ZONE
        if AVAILABILITY_ZONE is not None:
            zone_list = conn.describe_availability_zones().parse()
            if not zone_list:
                log.error('No availability zones found')
                return False

            zones = {}
            for zone in zone_list:
                zones[zone[1]] = zone[2]

            if not zones.has_key(AVAILABILITY_ZONE):
                log.error('AVAILABILITY_ZONE = %s does not exist' % AVAILABILITY_ZONE)
                return False
            elif zones[AVAILABILITY_ZONE] != 'available':
                log.error('The AVAILABILITY_ZONE = %s is not available at this time')
                return False
        return True

    def _has_valid_instance_type_settings(self):
        MASTER_IMAGE_ID = self.MASTER_IMAGE_ID
        NODE_IMAGE_ID = self.NODE_IMAGE_ID
        INSTANCE_TYPE = self.INSTANCE_TYPE
        instance_types = INSTANCE_TYPES
        conn = self.conn
        if not instance_types.has_key(INSTANCE_TYPE):
            log.error("You specified an invalid INSTANCE_TYPE %s \nPossible options are:\n%s" % (INSTANCE_TYPE,' '.join(instance_types.keys())))
            return False

        node_image_platform = conn.describe_images(imageIds=[NODE_IMAGE_ID]).parse()[0][6]
        instance_platform = instance_types[INSTANCE_TYPE]
        if instance_platform != node_image_platform:
            log.error('You specified an incompatible NODE_IMAGE_ID and INSTANCE_TYPE')
            log.error('INSTANCE_TYPE = %(instance_type)s is for a %(instance_platform)s \
    platform while NODE_IMAGE_ID = %(node_image_id)s is a %(node_image_platform)s platform' \
                        % { 'instance_type': INSTANCE_TYPE, 'instance_platform': instance_platform, \
                            'node_image_id': NODE_IMAGE_ID, 'node_image_platform': node_image_platform})
            return False
        
        if MASTER_IMAGE_ID is not None:
            master_image_platform = conn.describe_images(imageIds=[MASTER_IMAGE_ID]).parse()[0][6]
            if instance_platform != master_image_platform:
                log.error('You specified an incompatible MASTER_IMAGE_ID and INSTANCE_TYPE')
                log.error('INSTANCE_TYPE = %(instance_type)s is for a %(instance_platform)s \
    platform while MASTER_IMAGE_ID = %(master_image_id)s is a %(master_image_platform)s platform' \
                            % { 'instance_type': INSTANCE_TYPE, 'instance_platform': instance_platform, \
                                'image_id': MASETER_IMAGE_ID, 'master_image_platform': master_image_platform})
                return False
        
        return True

    def _has_valid_ebs_settings(self, cluster):
        #TODO check that ATTACH_VOLUME id exists
        ATTACH_VOLUME = cluster.ATTACH_VOLUME
        VOLUME_DEVICE = cluster.VOLUME_DEVICE
        VOLUME_PARTITION = cluster.VOLUME_PARTITION
        AVAILABILITY_ZONE = cluster.AVAILABILITY_ZONE
        conn = self.conn
        if ATTACH_VOLUME is not None:
            vol = conn.describe_volumes(volumeIds=[ATTACH_VOLUME]).parse()
            if not vol:
                log.error('ATTACH_VOLUME = %s does not exist' % ATTACH_VOLUME)
                return False
            vol = vol[0]
            if VOLUME_DEVICE is None:
                log.error('Must specify VOLUME_DEVICE when specifying ATTACH_VOLUME setting')
                return False
            if VOLUME_PARTITION is None:
                log.error('Must specify VOLUME_PARTITION when specifying ATTACH_VOLUME setting')
                return False
            if AVAILABILITY_ZONE is not None:
                vol_zone = vol[3]
                if vol.count(AVAILABILITY_ZONE) == 0:
                    log.error('The ATTACH_VOLUME you specified is only available in zone %(vol_zone)s, \
    however, you specified AVAILABILITY_ZONE = %(availability_zone)s\nYou need to \
    either change AVAILABILITY_ZONE or create a new volume in %(availability_zone)s' \
                                % {'vol_zone': vol_zone, 'availability_zone': AVAILABILITY_ZONE})
                    return False
        return True

    def _has_all_required_settings(self, cluster):
        has_all_required = True
        for opt in self.cluster_settings:
            name = opt[0]; required = opt[2]; default=opt[3]
            if required and cluster[name] is None:
                log.warn('Missing required setting %s under section [%s]' % (name,section_name))
                has_all_required = False
        return has_all_required

    def validate_aws_or_exit(self):
        conn = self.conn
        if conn is None or not self._has_valid_credentials():
            log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
            sys.exit(1)
        
    def validate_all_or_exit(self):
        for cluster in self.clusters:
            cluster = self.get_cluster(cluster)
            if not self.is_valid(cluster):
                log.error('configuration error...exiting')
                sys.exit(1)

    def _has_valid_credentials(self):
        conn = self.conn
        return not conn.describe_instances().is_error

    def _has_keypair(self, cluster):
        KEYNAME = cluster.KEYNAME
        conn = self.conn
        keypairs = conn.describe_keypairs().parse()
        has_keypair = False
        for key in keypairs:
            if key[1] == KEYNAME:
                has_keypair = True
        return has_keypair
