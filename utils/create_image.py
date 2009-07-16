#!/usr/bin/env python
import os
import pickle
from optparse import OptionParser

from starcluster import EC2
from starcluster.starclustercfg import *
from starcluster.ssh import Connection

class CreateEC2Image(object):

    def __init__(self):
        self.config_dict = None
        self.pickle_file = None
        self.conn = None
        self.env_variables = None

    def removeimage(self):
        #deregister the image
        self.conn.deregister_image(self.config_dict['image_to_remove'])
        os.system('ec2-delete-bundle -b %(bucket)s -p %(prefix)s -a %(access_key)s -s %(secret_key)s' % self.config_dict)

    def main(self):

        usage = "usage: %prog [options] "
        parser = OptionParser(usage)

        parser.add_option("-n","--host_number", dest="host_number", help="host number to use for making the image, counting from 0 (required)")
        parser.add_option("-b","--bucket", dest="bucket", help="name of the bucket to put the image in (required)")
        parser.add_option("-p","--prefix", dest="prefix", help="prefix for image files (eg 'my-image'). Defaults to 'image' (optional)")
        parser.add_option("-d","--delete_image", dest="image_to_remove", help="ami to remove from bucket (optional)")
        parser.add_option("-c","--credentials", dest="credentials", help="id_rsa file to use as credentials (optional)")

        (options,args) = parser.parse_args() 

        if options.host_number is not None:
            host_number = int(options.host_number)
        else: 
            host_number = None

        bucket = options.bucket
        image_to_remove = options.image_to_remove
        prefix = options.prefix

        if prefix is None:
            prefix = 'image'

        credentials = options.credentials

        # get location of certs from environment and setup configuration dictionary
        self.env_variables = dict(os.environ.items())
        EC2_PRIVATE_KEY = self.env_variables['EC2_PRIVATE_KEY']
        EC2_CERT = self.env_variables['EC2_CERT']

        # AWS-* variables imported from EC2Config.py 
        self.config_dict = { 'access_key': AWS_ACCESS_KEY_ID, 
                             'secret_key': AWS_SECRET_ACCESS_KEY, 
                             'private_key': os.path.split(EC2_PRIVATE_KEY)[-1], 
                             #'private_key': EC2_PRIVATE_KEY,
                             'userid': AWS_USER_ID, 
                             'cert': os.path.split(EC2_CERT)[-1], 
                             #'cert': EC2_CERT,
                             'bucket': bucket, 
                             'prefix': prefix,
                             'credentials': credentials,
                             'host_number': host_number,
                             'image_to_remove': image_to_remove,
                             'image_host': None }

        self.conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        
        if image_to_remove:
            if prefix is None or bucket is None:
                print 'Must provide the prefix and bucket for the image you want to delete.  Not deleting...'
            else:
                print 'Deleting image: %s' % image_to_remove
                self.removeimage()
                print 'Done deleting image...exiting'
                return

        if host_number is None or bucket is None:
            print 'ERROR: Must provide both -n and -b options.  Pass --help for details'
            return 
        

        self.getimagehost()
        if self.config_dict['image_host'] is None:
            return
        self.pickleconfig()
        self.transferfiles()
        self.bundleandregister()
        os.unlink('config.pkl') 
        print 'exiting'

    def pickleconfig(self):
        # Pickle the config dictionary so we can scp it to the host for prepare-instance.py to use
        self.pickle_file = 'config.pkl'
        fd = open(self.pickle_file,'w')
        pickle.dump(self.config_dict, fd)
        fd.close()

    def transferfiles(self):
        # get image host and required credentials (if any)
        image_host = self.config_dict['image_host']
        credentials = self.config_dict['credentials']

        # copy keys over to host along with the config pickle 
        EC2_PRIVATE_KEY = self.env_variables['EC2_PRIVATE_KEY']
        EC2_CERT = self.env_variables['EC2_CERT']
        conn = Connection(image_host,'root', credentials)
        conn.put(EC2_PRIVATE_KEY, "/mnt/" + os.path.basename(EC2_PRIVATE_KEY))
        conn.put(EC2_CERT, "/mnt/" + os.path.basename(EC2_CERT))
        conn.put(self.pickle_file, "/mnt/" + os.path.basename(self.pickle_file))

        # copy over script to host that will take care of creating the image and cleaning up properly
        conn.put("prepare-instance.py", "/mnt/prepare-instance.py")
        conn.close()

    def bundleandregister(self):
        # run script to prepare the host
        image_host = self.config_dict['image_host']
        credentials = self.config_dict['credentials']
        #conn = Connection(image_host,'root', credentials)
        #print conn.execute("python /mnt/prepare-instance.py")
        # using system ssh here since it's better to see the output realtime than after the fact
        os.system('ssh -i %s root@%s python /mnt/prepare-instance.py' % (credentials, image_host))
        # register compute node image we just created
        self.conn.register_image("%(bucket)s/%(prefix)s.manifest.xml" % self.config_dict)
    
    def getimagehost(self):
        # get name of host to image
        instances = [] 
        for instance in self.conn.describe_instances().parse():
            if instance[0] == 'INSTANCE':
                instances.append(instance)

        #list_host_status = [(i[3],i[5]) for i in self.conn.describe_instances().parse()[1::2]] # list of hosts and their status
        list_host_status = [(i[3],i[5]) for i in instances] # list of hosts and their status
        running_hosts = [] 

        for host in list_host_status:
            if host[1] == 'running':
                running_hosts.append(host[0])    

        try:
            image_host = running_hosts[self.config_dict['host_number']]
        except IndexError:
            print """
                ERROR: host #%s either doesn't exist or is not running.
                       Please check ec2-describe-instances and try again"
            """ % host_number
            image_host = None 

        self.config_dict['image_host'] = image_host
        print "IMAGE HOST: %s" % image_host

if __name__ == '__main__':
    create_image = CreateEC2Image()
    create_image.main()
