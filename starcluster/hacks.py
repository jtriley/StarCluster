# Hacks file (fix me!)

# this is a temporary hack until the next version of boto. ImageLocation is
# wrong in boto-1.9d
from boto.resultset import ResultSet
def register_image(conn, name=None, description=None, image_location=None,
                   architecture=None, kernel_id=None, ramdisk_id=None,
                   root_device_name=None, block_device_map=None):
    """
    Register an image.

    :type name: string
    :param name: The name of the AMI.  Valid only for EBS-based images.

    :type description: string
    :param description: The description of the AMI.

    :type image_location: string
    :param image_location: Full path to your AMI manifest in Amazon S3 storage.
    Only used for S3-based AMI's.

    :type architecture: string
    :param architecture: The architecture of the AMI.  
    Valid choices are: i386 | x86_64

    :type kernel_id: string
    :param kernel_id: The ID of the kernel with which to launch the instances

    :type root_device_name: string
    :param root_device_name: The root device name (e.g. /dev/sdh)

    :type block_device_map: :class:`boto.ec2.blockdevicemapping.BlockDeviceMapping`
    :param block_device_map: 
    A BlockDeviceMapping data structure describing the EBS volumes associated
    with the Image.

    :rtype: string
    :return: The new image id
    """
    params = {}
    if name:
        params['Name'] = name
    if description:
        params['Description'] = description
    if architecture:
        params['Architecture'] = architecture
    if kernel_id:
        params['KernelId'] = kernel_id
    if ramdisk_id:
        params['RamdiskId'] = ramdisk_id
    if image_location:
        params['ImageLocation'] = image_location
    if root_device_name:
        params['RootDeviceName'] = root_device_name
    if block_device_map:
        block_device_map.build_list_params(params)
    rs = conn.get_object('RegisterImage', params, ResultSet)
    image_id = getattr(rs, 'imageId', None)
    return image_id
