from starcluster.utils import AttributeDict

class Cluster(AttributeDict):

    @property
    def conn(self):  
        if self._conn is None:
            if self.aws.AWS_ACCESS_KEY_ID is None or self.aws.AWS_SECRET_ACCESS_KEY is None:
                return None
            else:
                self._conn = EC2.AWSAuthConnection(self.aws.AWS_ACCESS_KEY_ID, self.aws.AWS_SECRET_ACCESS_KEY)
        return self._conn

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

    def _has_valid_instance_type_settings(self, cluster):
        MASTER_IMAGE_ID = cluster.MASTER_IMAGE_ID
        NODE_IMAGE_ID = cluster.NODE_IMAGE_ID
        INSTANCE_TYPE = cluster.INSTANCE_TYPE
        instance_types = self.instance_types
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
