default_config = {
    'default': 'smallcluster',
    'enable_experimental': 'False',
    'aws_access_key_id': 'asd0asd9f0asd0fas0d9f0',
    'aws_secret_access_key': 'asdf0a9sdf09203fj0asdf',
    'aws_user_id': 9009230923,
    'k1_location': '~/.path/to/k1_rsa',
    'k2_location': '/path/to/k2_rsa',
    'k3_location': '/path/to/k3_rsa',
    'v1_id': 'vol-c999999',
    'v1_device': '/dev/sdj',
    'v1_partition': 1,
    'v1_mount_path': '/volume1',
    'v2_id': 'vol-c888888',
    'v2_device': '/dev/sdk',
    'v2_partition': 1,
    'v2_mount_path': '/volume2',
    'v3_id': 'vol-c777777',
    'v3_device': '/dev/sdl',
    'v3_partition': 1,
    'v3_mount_path': '/volume3',
    'v4_id': 'vol-c666666',
    'v4_partition': 1,
    'v4_mount_path': '/volume4',
    'v5_id': 'vol-c555555',
    'v5_partition': 1,
    'v5_mount_path': '/volume5',
    'p1_class': 'starcluster.tests.mytestplugin.SetupClass',
    'p1_param1': 23,
    'p1_param2': 'skidoo',
    'p2_class': 'starcluster.tests.mytestplugin.SetupClass2',
    'p2_param1': 'hello',
    'p2_param2': 'world',
    'p3_class': 'starcluster.tests.mytestplugin.SetupClass3',
    'p3_param1': 'bon',
    'p3_param2': 'jour',
    'p3_param3': 'monsignour',
    's1_protocol': 'udp',
    's1_from_port': 20,
    's1_to_port': 20,
    's1_cidr_ip': '192.168.1.0/24',
    's2_protocol': 'tcp',
    's2_from_port': 80,
    's2_to_port': 20,
    's2_cidr_ip': '192.168.233.0/24',
    's3_from_port': 20,
    's3_to_port': 30,
    'c1_keyname': 'k1',
    'c1_size': 4,
    'c1_user': 'testuser',
    'c1_shell': 'zsh',
    'c1_master_id': 'ami-8f9e71e6',
    'c1_node_id': 'ami-8f9e71e6',
    'c1_master_type': 'm1.small',
    'c1_node_type': 'm1.small',
    'c1_vols': 'v1,v2,v3',
    'c1_plugs': 'p1,p2,p3',
    'c1_zone': 'us-east-1c',
    'c2_extends': 'c1',
    'c2_keyname': 'k2',
    'c2_size': 6,
    'c2_master_type': 'c1.xlarge',
    'c2_node_type': 'c1.xlarge',
    'c2_vols': 'v1,v2',
    'c3_extends': 'c2',
    'c3_keyname': 'k3',
    'c3_size': 8,
    'c3_vols': 'v3',
    'c4_extends': 'c3',
    'c4_permissions': 's1',
}

config_test_template = """
[global]
DEFAULT=%(default)s
ENABLE_EXPERIMENTAL=%(enable_experimental)s

[aws info]
AWS_ACCESS_KEY_ID = %(aws_access_key_id)s
AWS_SECRET_ACCESS_KEY = %(aws_secret_access_key)s
AWS_USER_ID= %(aws_user_id)s

[key k1]
KEY_LOCATION=%(k1_location)s

[key k2]
KEY_LOCATION=%(k2_location)s

[key k3]
KEY_LOCATION=%(k3_location)s

[volume v1]
VOLUME_ID = %(v1_id)s
DEVICE = %(v1_device)s
PARTITION = %(v1_partition)s
MOUNT_PATH = %(v1_mount_path)s

[volume v2]
VOLUME_ID = %(v2_id)s
DEVICE = %(v2_device)s
PARTITION = %(v2_partition)s
MOUNT_PATH = %(v2_mount_path)s

[volume v3]
VOLUME_ID = %(v3_id)s
DEVICE = %(v3_device)s
PARTITION = %(v3_partition)s
MOUNT_PATH = %(v3_mount_path)s

[volume v4]
VOLUME_ID = %(v4_id)s
PARTITION = %(v4_partition)s
MOUNT_PATH = %(v4_mount_path)s

[volume v5]
VOLUME_ID = %(v5_id)s
PARTITION = %(v5_partition)s
MOUNT_PATH = %(v5_mount_path)s

[plugin p1]
SETUP_CLASS = %(p1_class)s
MY_ARG = %(p1_param1)s
MY_OTHER_ARG = %(p1_param2)s

[plugin p2]
SETUP_CLASS = %(p2_class)s
MY_ARG = %(p2_param1)s
MY_OTHER_ARG = %(p2_param2)s

[plugin p3]
SETUP_CLASS = %(p3_class)s
MY_ARG = %(p3_param1)s
MY_OTHER_ARG = %(p3_param2)s
MY_OTHER_OTHER_ARG = %(p3_param3)s

[permission s1]
protocol = %(s1_protocol)s
from_port = %(s1_from_port)s
to_port = %(s1_to_port)s
cidr_ip = %(s1_cidr_ip)s

[permission s2]
protocol = %(s2_protocol)s
from_port = %(s2_from_port)s
to_port = %(s2_to_port)s
cidr_ip = %(s2_cidr_ip)s

[permission s3]
from_port = %(s3_from_port)s
to_port = %(s3_to_port)s

[cluster c1]
KEYNAME = %(c1_keyname)s
CLUSTER_SIZE = %(c1_size)s
CLUSTER_USER = %(c1_user)s
CLUSTER_SHELL = %(c1_shell)s
MASTER_IMAGE_ID = %(c1_master_id)s
MASTER_INSTANCE_TYPE = %(c1_master_type)s
NODE_IMAGE_ID = %(c1_node_id)s
NODE_INSTANCE_TYPE = %(c1_node_type)s
AVAILABILITY_ZONE = %(c1_zone)s
VOLUMES = %(c1_vols)s
PLUGINS = %(c1_plugs)s

[cluster c2]
EXTENDS=%(c2_extends)s
KEYNAME = %(c2_keyname)s
CLUSTER_SIZE= %(c2_size)s
MASTER_INSTANCE_TYPE = %(c2_master_type)s
NODE_INSTANCE_TYPE = %(c2_node_type)s
VOLUMES = %(c2_vols)s

[cluster c3]
EXTENDS=%(c3_extends)s
KEYNAME = %(c3_keyname)s
CLUSTER_SIZE= %(c3_size)s
VOLUMES = %(c3_vols)s

[cluster c4]
EXTENDS=%(c4_extends)s
PERMISSIONS=%(c4_permissions)s
"""
