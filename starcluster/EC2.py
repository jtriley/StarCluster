#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon Web
#  Services LLC or its affiliates with respect to your use of this software
#  code. (c) 2006 Amazon Web Services LLC or its affiliates.  All rights
#  reserved.

import base64
import hmac
import httplib
import re
#import sha
from hashlib import sha1 as sha
import sys
import time
import urllib
# ElementTree is in stdlib from Python 2.5, so get it from there if we can:
try:
    from xml.etree import ElementTree as ET
except ImportError:
    from elementtree import ElementTree as ET

DEFAULT_HOST = 'ec2.amazonaws.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
#API_VERSION = '2008-02-01'
#RELEASE_VERSION = "22395"
API_VERSION='2008-12-01'
RELEASE_VERSION = "30349"

class AWSAuthConnection(object):

    """
    Creates an authorized connection to EC2 containing wrappers for
    Query API calls.

    Each API call has a matching method on this class to perform the
    appropriate E2 action.

    @ivar verbose: Verbosity flag, defaults to false.  If set to true,
    some debug information is printed.

    """
    
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 is_secure=True, server=DEFAULT_HOST, port=None):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.verbose = False
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        if (is_secure):
            self.connection = httplib.HTTPSConnection("%s:%d" % (server, port))
        else:
            self.connection = httplib.HTTPConnection("%s:%d" % (server, port))

    def pathlist(self, key, arr):
        """Converts a key and an array of values into AWS query param format."""
        params = {}
        i = 0
        for value in arr:
            i += 1
            params["%s.%s" % (key, i)] = value
        return params

    def allocate_address(self):
        """Makes an C{AllocateAddress} call.

        """
        params = {}
        return AllocateAddressResponse(self.make_request("AllocateAddress", params))

    def describe_addresses(self, publicIps=None):
        """Makes a C{DescribeAddresses} call.

        @param publicIps: List of addresses to describe.  If empty or
        omitted, all addresses will be described.

        """
        if publicIps == None: publicIps = []
        params = self.pathlist("PublicIp", publicIps)
        return DescribeAddressesResponse(self.make_request("DescribeAddresses", params))

    def release_address(self, publicIp):
        """Makes a C{ReleaseAddress} call.

        @param publicIp: Address to release

        """
        params = { "PublicIp": publicIp }
        return ReleaseAddressResponse(self.make_request("ReleaseAddress", params))

    def associate_address(self, publicIp, instanceId):
        """Makes an C{AssociateAddress} call.

        @param publicIp: Address to associate
        @param instanceId: Instance to associate address with

        """
        params = { "PublicIp": publicIp, "InstanceId": instanceId }
        return AssociateAddressResponse(self.make_request("AssociateAddress", params))

    def disassociate_address(self, publicIp):
        """Makes a C{DisassociateAddress} call.

        @param publicIp: Address to disassociate

        """
        params = { "PublicIp": publicIp }
        return DisassociateAddressResponse(self.make_request("DisassociateAddress", params))

    def describe_availability_zones(self, zoneNames=None):
        """Makes a C{DescribeAvailabilityZones} call.

        @param zoneNames: List of availability zones to describe.  If
        empty or omitted, all availability zones will be described.

        """
        if zoneNames == None: zoneNames = []
        params = self.pathlist("ZoneName", zoneNames)
        return DescribeAvailabilityZonesResponse(self.make_request("DescribeAvailabilityZones", params))


    def register_image(self, imageLocation):
        """Makes a C{RegisterImage} call.

        @param imageLocation: The location of the image manifest to
        register in S3.
        
        """
        params = { "ImageLocation": imageLocation }
        return RegisterImageResponse(self.make_request("RegisterImage", params))

    def describe_images(self, imageIds=None, owners=None, executableBy=None):
        """Makes a C{DescribeImages} call.

        @param imageIds: List of images to describe.  If empty or omitted, all
        images visible to the user are returned.

        @param owners: List of users to filter returned images by
        owner.  If empty or omitted, no filtering is done.

        @param executableBy: List of users (or user groups) to filter
        returned images by execution permissions.  If empty or
        omitted, no filtering is done.

        """
        if imageIds == None: imageIds = []
        if owners == None: owners = []
        if executableBy == None: executableBy = []
        params = self.pathlist("ImageId", imageIds)
        params.update(self.pathlist("Owner", owners))
        params.update(self.pathlist("ExecutableBy", executableBy))
        return DescribeImagesResponse(self.make_request("DescribeImages", params))

    def deregister_image(self, imageId):
        """Makes a C{DeregisterImage} call.

        @param imageId: The image id to deregister.

        """
        params = { "ImageId": imageId }
        return DeregisterImageResponse(self.make_request("DeregisterImage", params))

    def create_keypair(self, keyName):
        """Makes a C{CreateKeypair} call.

        @param keyName: Name for the new keypair.

        """
        params = { "KeyName": keyName }
        return CreateKeyPairResponse(self.make_request("CreateKeyPair", params))

    def describe_keypairs(self, keyNames=None):
        """Makes a C{DescribeKeypairs} call.

        @param keyNames: List of keypairs to describe.  If empty or
        omitted, all keypairs are returned.

        """
        if keyNames == None: keyNames = []
        params = self.pathlist("KeyName", keyNames)
        return DescribeKeyPairsResponse(self.make_request("DescribeKeyPairs", params))

    def delete_keypair(self, keyName):
        """Makes a C{DeleteKeypair} call.

        @param keyName: Name of keypair to delete.

        """

        params = { "KeyName": keyName }
        return DeleteKeyPairResponse(self.make_request("DeleteKeyPair", params))

    def run_instances(self, imageId, minCount=1, maxCount=1, keyName=None,
                      groupIds=None, userData=None, base64Encode=True,
                      addressingType=None, instanceType=None,
                      availabilityZone=None, kernelId=None, ramdiskId=None,
                      blockDeviceMapping=None):
        """Makes a C{RunInstances} call.

        @param imageId: AMI id to launch instances of.

        @param minCount: Minimum number of instances to launch.  If
        EC2 cannot launch at least this many, the call will fail.

        @param maxCount: Maximum number of instances to launch.  EC2
        will make a best-effort attempt to launch this many instances,
        but will not fail unless fewer than C{minCount} are available.

        @param keyName: Name of keypair to launch instances with.

        @param groupIds: List of security groups to launch instances
        in.

        @param userData: String containing user data to inject into
        launched instances.

        @param base64Encode: Specifies whether C{userData} string
        qshould be base64 encoded.  Defaults to True.

        @param addressingType: Specifies the address scheme to use for
        the instance. The supported (default) type is C{"public"}, or
        C{None} for the default. See the "Instance Addressing" section
        of the latest developer guide for more information.

        @param availabilityZone: Specifies the availability zone to
        launch in.

        @param kernelId: Kernel to launch the instances with.

        @param ramdiskId: Ramdisk to launch the instances with.

        @param blockDeviceMapping: Specifies the virtual block device
        mapping. This parameter is a list of two element lists or
        tuples. The first element is the virtual name and the second
        is the device name.

        """
        if groupIds == None: groupIds = []
        params = {
            "ImageId": imageId,
            "MinCount": str(minCount),
            "MaxCount": str(maxCount),
            }
        if addressingType is not None:
            params["AddressingType"] = addressingType
        params.update(self.pathlist("SecurityGroup", groupIds))
        if userData is not None:
            if base64Encode:
                userData = base64.encodestring(userData)
            params["UserData"] = userData
        if keyName is not None:
            params["KeyName"] = keyName
        if availabilityZone is not None:
            params["Placement.AvailabilityZone"] = availabilityZone
        if kernelId is not None:
            params["KernelId"] = kernelId
        if ramdiskId is not None:
            params["RamdiskId"] = ramdiskId
        if instanceType is not None:
            params["InstanceType"] = instanceType
        if blockDeviceMapping is not None:
            virtualNames, deviceNames = zip(*blockDeviceMapping)
            i = 0
            for value in arr:
                i += 1
                params["BlockDeviceMapping.%s.VirtualName" % (i)] = virtualNames[i]
                params["BlockDeviceMapping.%s.DeviceName" % (i)] = deviceNames[i]
            
        return RunInstancesResponse(self.make_request("RunInstances", params))

    def attach_volume(self, volumeId, instanceId, device):
        """Makes a C{AttachVolume} call.

        @param volumeId: The ID of the Amazon EBS volume

        @param instanceId: The ID of the instance from which the volume will detach

        @param device:  The device name
        """ 
        params = {'VolumeId': volumeId, 'InstanceId': instanceId, 'Device': device}
        return AttachVolumeResponse(self.make_request("AttachVolume", params))

    def detach_volume(self, volumeId, instanceId = '', device = '', force = False):
        """Makes a C{DetachVolume} call.

        @param volumeId: The ID of the Amazon EBS volume

        @param instanceId: The ID of the instance from which the volume will detach

        @param device:  The device name

        @param force: Forces detachment if the previous detachment attempt 
        did not occur cleanly (logging into an instance, unmounting the volume, 
        and detaching normally). This option can lead to data loss or a corrupted 
        file system. Use this option only as a last resort to detach a volume from 
        a failed instance. The instance will not have an opportunity to flush file
        system caches nor file system meta data. If you use this option, you must 
        perform file system check and repair procedures.
        """ 
        params = {'VolumeId': volumeId, 'InstanceId': instanceId, 'Device':device}
        
        if force:
            params['Force'] = 'true'
        return DetachVolumeResponse(self.make_request("DetachVolume", params))
    

    def describe_instances(self, instanceIds=[]):
        """Makes a C{DescribeInstances} call.

        @param instanceIds: List of instances to describe.  If empty
        or omitted, all instances will be returned.

        """
        params = self.pathlist("InstanceId", instanceIds)
        return DescribeInstancesResponse(self.make_request("DescribeInstances", params))

    def describe_volumes(self, volumeIds=[]):
        """Makes a C{DescribeVolumes} call.

        @param volumeIds: List of volumes.  If empty
        or omitted, all volumes will be returned.

        """
        params = self.pathlist("VolumeId", volumeIds)
        return DescribeVolumesResponse(self.make_request("DescribeVolumes", params))
        

    def get_console_output(self, instanceId):
        """Makes a C{GetConsoleOutput} call.

        @param instanceId: Instance from which to get console output.

        """
        params = { "InstanceId": instanceId }
        return GetConsoleOutputResponse(self.make_request("GetConsoleOutput", params))

    def reboot_instances(self, instanceIds):
        """Makes a C{RebootInstances} call.

        @param instanceIds: List of instances to reboot.

        """
        params = self.pathlist("InstanceId", instanceIds)
        return RebootInstancesResponse(self.make_request("RebootInstances", params))

    def terminate_instances(self, instanceIds):
        """Makes a C{TerminateInstances} call.

        @param instanceIds: List of instances to terminate.

        """
        params = self.pathlist("InstanceId", instanceIds)
        return TerminateInstancesResponse(self.make_request("TerminateInstances", params))

    def create_securitygroup(self, groupName, groupDescription):
        """Makes a C{CreateSecurityGroup} call.

        @param groupName: Name of group to create.

        @param groupDescription: Brief description of security group.

        """
        params = {
            "GroupName": groupName,
            "GroupDescription": groupDescription
            }
        return CreateSecurityGroupResponse(self.make_request("CreateSecurityGroup", params))

    def describe_securitygroups(self, groupNames=None):
        """Makes a C{DescribeSecurityGroups} call.

        @param groupNames: List of security groups to describe.  If
        empty or omitted, all security groups will be described.

        """
        if groupNames == None: groupNames = []
        params = self.pathlist("GroupName", groupNames)
        return DescribeSecurityGroupsResponse(self.make_request("DescribeSecurityGroups", params))

    def delete_securitygroup(self, groupName):
        """Makes a C{DeleteSecurityGroup} call.

        @param groupName: Name of security group to delete.

        """
        params = { "GroupName": groupName }
        return DeleteSecurityGroupResponse(self.make_request("DeleteSecurityGroup", params))

    def authorize(self, *args, **kwargs):
        """Makes an C{AuthorizeSecurityGroupIngress} call.

        L{authorize} and L{revoke} share parameter parsing code.
        See L{auth_revoke_impl} for parameters.  Also, see API docs
        for details of valid parameter combinations.

        """
        params = self.auth_revoke_impl(*args, **kwargs)
        return AuthorizeSecurityGroupIngressResponse(self.make_request("AuthorizeSecurityGroupIngress", params))

    def revoke(self, *args, **kwargs):
        """Makes an C{RevokeSecurityGroupIngress} call.

        L{authorize} and L{revoke} share parameter parsing code.
        See L{auth_revoke_impl} for parameters.  Also, see API docs
        for details of valid parameter combinations.

        """
        params = self.auth_revoke_impl(*args, **kwargs)
        return RevokeSecurityGroupIngressResponse(self.make_request("RevokeSecurityGroupIngress", params))

    def modify_image_attribute(self, imageId, attribute, operationType,
                               **kwargs):
        """Makes a C{ModifyImageAttribute} call.

        @param imageId: AMI to modify attribute of.

        @param attribute: Name of attribute to modify.

        @param operationType: Operation to perform on attribute.

        @param kwargs: Values for the attribute operation, documented below.

        @kwarg userIds: List of userIds (valid with
        C{'launchPermission'} attribute.)

        @kwarg userGroups: List of userGroups (valid with
        C{'launchPermission'} attribute.)

        """
        params = {
            "ImageId": imageId,
            "Attribute": attribute,
            "OperationType": operationType
            }
        if attribute == "launchPermission":
            if "userIds" in kwargs:
                params.update(self.pathlist("UserId", kwargs["userIds"]))
            if "userGroups" in kwargs:
                params.update(self.pathlist("UserGroup", kwargs["userGroups"]))
        elif attribute == "productCodes":
            if "productCodes" in kwargs:
                params.update(self.pathlist("ProductCode", kwargs["productCodes"]))
        return ModifyImageAttributeResponse(self.make_request("ModifyImageAttribute", params))
    
    def reset_image_attribute(self, imageId, attribute):
        """Makes a C{ResetImageAttribute} call.

        @param imageId: AMI to reset attribute of.

        @param attribute: Name of attribute to reset.

        """
        params = { "ImageId": imageId, "Attribute": attribute }
        return ResetImageAttributeResponse(self.make_request("ResetImageAttribute", params))
    
    def describe_image_attribute(self, imageId, attribute):
        """Makes a C{DescribeImageAttribute} call.

        @param imageId: AMI to describe attribute of.

        @param attribute: Name of attribute to describe.

        """
        params = { "ImageId": imageId, "Attribute": attribute }
        return DescribeImageAttributeResponse(self.make_request("DescribeImageAttribute", params))

    def auth_revoke_impl(self, groupName, ipProtocol=None, fromPort=None,
                         toPort=None, cidrIp=None,
                         sourceSecurityGroupName=None,
                         sourceSecurityGroupOwnerId=None):
        """Processes parameters for C{authorize} and C{revoke}.

        @param groupName: Name of security group to modify.

        @param ipProtocol: IP protocol in rule.  Valid vlaues are
        C{'tcp'}, C{'udp'} and C{'icmp'}.

        @param fromPort: Bottom of IP port range in rule.

        @param toPort: Top of IP port range in rule.

        @param cidrIp: CIDR IP range in rule.

        @param sourceSecurityGroupName: Security group name in rule.

        @param sourceSecurityGroupOwnerId: User id of security group
        in rule.

        """
        params = { "GroupName": groupName }
        if ipProtocol != None: params["IpProtocol"] = ipProtocol
        if fromPort != None: params["FromPort"] = str(fromPort)
        if toPort != None: params["ToPort"] = str(toPort)
        if cidrIp != None: params["CidrIp"] = cidrIp
        if sourceSecurityGroupName != None:
            params["SourceSecurityGroupName"] = sourceSecurityGroupName
        if sourceSecurityGroupOwnerId != None:
            params["SourceSecurityGroupOwnerId"] = sourceSecurityGroupOwnerId
        return params

    def confirm_product_instance(self, productCode, instanceId):
        """Makes a C{ConfirmProdcutInstance} call.

        @param productCode: The product code to confirm

        @param instanceId: The instance for which to confirm the product code.
        
        """
        params = { "ProcudtCode": productCode, "InstanceId": instanceId }
        return ConfirmProductInstanceResponse(self.make_request("ConfirmProductInstance", params))

    def make_request(self, action, params, data=''):
        params["Action"] = action
        if self.verbose:
            print params

        params["SignatureVersion"] = "1"
        params["AWSAccessKeyId"] = self.aws_access_key_id
        params["Version"] = API_VERSION
        params["Timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        params = zip(params.keys(), params.values())
        params.sort(key=lambda x: str.lower(x[0]))
        
        sig = self.get_aws_auth_param(params, self.aws_secret_access_key)

        path = "?%s&Signature=%s" % (
            "&".join(["=".join([param[0], urllib.quote_plus(param[1])]) for param in params]),
            sig)

        if self.verbose:
            print path

        headers = {
            'User-Agent': 'ec2-python-query 1.2-%s' % (RELEASE_VERSION)
            }

        try:
            self.connection.request("GET", "/%s" % path, data, headers)
            return self.connection.getresponse()
        except Exception,e:
            print 'Error making request. Check your internet connection?'
            sys.exit(1)
            #from IPython.Shell import IPShellEmbed
            #ipshell = IPShellEmbed(user_ns = dict(self=self))
            #ipshell()

    def get_aws_auth_param(self, params, aws_secret_access_key):
        canonical_string = "".join(["".join(param) for param in params])
        return self.encode(aws_secret_access_key, canonical_string)

    # computes the base64'ed hmac-sha hash of the canonical string and
    # the secret access key, optionally urlencoding the result

    def encode(self, aws_secret_access_key, str, urlencode=True):
        b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, sha).digest()).strip()
        if urlencode:
            return urllib.quote_plus(b64_hmac)
        else:
            return b64_hmac



class Response(object):
    """Base class for XML response parsers.

    This class does everything except the API-call dependent parsing,
    which is handled in the child classes below.  Each child class
    should override the L{parse} method.
    
    """

    ERROR_XPATH = "Errors/Error"
    NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

    def __init__(self, http_response):
        self.http_response = http_response
        self.http_xml = http_response.read()
        self.is_error = False
        if http_response.status == 200:
            self.structure = self.parse()
        else:
            self.is_error = True
            self.structure = self.parse_error()

    def parse_error(self):
        doc = ET.XML(self.http_xml)
        element = doc.find(self.ERROR_XPATH)
        errorCode = element.findtext("Code")
        errorMessage = element.findtext("Message")
        return [["%s: %s" % (errorCode, errorMessage)]]

    def parse(self):
        # Placeholder -- this method should be overridden in child classes.
        return None

    def __str__(self):
        return "\n".join(["\t".join(line) for line in self.structure])

    def fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (self.NAMESPACE, e) for e in xpath.split("/")])

    def findtext(self, element, xpath):
        return element.findtext(self.fixxpath(xpath))

    def findall(self, element, xpath):
        return element.findall(self.fixxpath(xpath))

    def find(self, element, xpath):
        return element.find(self.fixxpath(xpath))

    def fixnone(self, strnone):
        if strnone is None: return ""
        return strnone


class DescribeImagesResponse(Response):
    """Response parser class for C{DescribeImages} API call."""
    ELEMENT_XPATH = "imagesSet/item"
    def translate_isPublic(self, isPublic):
        return { "true": "public",
                 "false": "private" }[isPublic]
    
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for element in self.findall(doc, self.ELEMENT_XPATH):
            lines.append(["IMAGE",
                          self.findtext(element, "imageId"),
                          self.findtext(element, "imageLocation"),
                          self.findtext(element, "imageOwnerId"),
                          self.findtext(element, "imageState"),
                          self.translate_isPublic(self.findtext(element, "isPublic")),
                          self.findtext(element, "architecture"),
                          self.findtext(element, "imageType"),
                          self.fixnone(self.findtext(element, "kernelId")),
                          self.fixnone(self.findtext(element, "ramdiskId")),
                          ])
        return lines


class RegisterImageResponse(Response):
    """Response parser class for C{RegisterImage} API call."""
    ELEMENT_XPATH = "imageId"
    def parse(self):
        doc = ET.XML(self.http_xml)
        return [["IMAGE", self.findtext(doc, self.ELEMENT_XPATH)]]


class DeregisterImageResponse(Response):
    """Response parser class for C{DeregisterImage} API call."""
    def parse(self):
        # If we don't get an error, the deregistration succeeded.
        return [["Image deregistered."]]


class CreateKeyPairResponse(Response):
    """Response parser class for C{CreateKeyPair} API call."""
    def parse(self):
        doc = ET.XML(self.http_xml)
        keyName = self.findtext(doc, "keyName")
        keyFingerprint = self.findtext(doc, "keyFingerprint")
        keyMaterial = self.findtext(doc, "keyMaterial")
        return [["KEYPAIR", keyName, keyFingerprint], [keyMaterial]]


class DescribeKeyPairsResponse(Response):
    """Response parser class for C{DescribeKeyPairs} API call."""
    ELEMENT_XPATH = "keySet/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for element in self.findall(doc, self.ELEMENT_XPATH):
            keyName = self.findtext(element, "keyName")
            keyFingerprint = self.findtext(element, "keyFingerprint")
            lines.append(["KEYPAIR", keyName, keyFingerprint])
        return lines


class DeleteKeyPairResponse(Response):
    """Response parser class for C{DeleteKeyPair} API call."""
    def parse(self):
        # If we don't get an error, the deletion succeeded.
        return [["Keypair deleted."]]

class AttachmentSetResponse(Response):
    """ Response containing attachment set items """
    def parseAttachmentSet(self, root):
        """ Parse a set of attachmentSet/item nodes """
        lines = []
        for element in self.findall(root, "attachmentSet/item"):
            lines.append(["ATTACHMENT",
                          self.findtext(element, "volumeId"),
                          self.findtext(element, "instanceId"),
                          self.fixnone(self.findtext(element, "device")),
                          self.fixnone(self.findtext(element, "size")),
                          self.findtext(element, "status"),
                          self.findtext(element, "attachTime"),
                          ])
        return lines

class AttachmentResponse(Response):
    def parseAttachment(self):
        doc = ET.XML(self.http_xml)
        lines = []
        lines.append(["ATTACHMENT",
                      self.findtext(doc, "volumeId"),
                      self.findtext(doc, "instanceId"),
                      self.fixnone(self.findtext(doc, "device")),
                      self.fixnone(self.findtext(doc, "size")),
                      self.findtext(doc, "status"),
                      self.findtext(doc, "attachTime"),
                      ])
        return lines

class InstanceSetResponse(Response):
    """ Response containing instance set items """
    def parseInstanceSet(self, root):
        """ Parse a set of instanceSet/item nodes """
        lines = []
        for element in self.findall(root, "instancesSet/item"):
            lines.append(["INSTANCE",
                          self.findtext(element, "instanceId"),
                          self.findtext(element, "imageId"),
                          self.findtext(element, "dnsName"),
                          self.findtext(element, "privateDnsName"),
                          self.findtext(element, "instanceState/name"),
                          self.fixnone(self.findtext(element, "keyName")),
                          self.findtext(element, "amiLaunchIndex"),
                          ",".join([p.text for p in self.findall(element, "productCodesSet/item/productCode")]),
                          self.findtext(element, "instanceType"),
                          self.findtext(element, "launchTime"),
                          self.findtext(element, "placement/availabilityZone"),
                          self.fixnone(self.findtext(element, "kernelId")),
                          self.fixnone(self.findtext(element, "ramdiskId")),
                          ])
        return lines

class RunInstancesResponse(InstanceSetResponse):
    """Response parser class for C{RunInstances} API call."""
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        reservationId = self.findtext(doc, "reservationId")
        ownerId = self.findtext(doc, "ownerId")
        groups = [g.text for g in self.findall(doc, "groupSet/item/groupId")]
        lines.append(["RESERVATION", reservationId, ownerId, ",".join(groups)])
        lines.extend(self.parseInstanceSet(doc))
        return lines

class DetachVolumeResponse(AttachmentResponse):
    """Response parser class for C{DetachVolume} API call."""
    def parse(self):
        return self.parseAttachment()

class AttachVolumeResponse(AttachmentResponse):
    """Response parser class for C{AttachVolume} API call."""
    def parse(self):
        return self.parseAttachment()
        

class DescribeInstancesResponse(InstanceSetResponse):
    """Response parser class for C{DescribeInstances} API call."""
    ELEMENT_XPATH = "reservationSet/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for rootelement in self.findall(doc, self.ELEMENT_XPATH):
            reservationId = self.findtext(rootelement, "reservationId")
            ownerId = self.findtext(rootelement, "ownerId")
            groups = [g.text for g in self.findall(rootelement, "groupSet/item/groupId")]
            lines.append(["RESERVATION", reservationId, ownerId, ",".join(groups)])
            lines.extend(self.parseInstanceSet(rootelement))
        return lines

class DescribeVolumesResponse(AttachmentSetResponse):
    """Response parser class for C{DescribeVolumes} API call."""
    ELEMENT_XPATH = "volumeSet/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for rootelement in self.findall(doc, self.ELEMENT_XPATH):
            volumeId = self.findtext(rootelement, "volumeId")
            size = self.findtext(rootelement, "size")
            status = self.findtext(rootelement, "status")
            availability_zone = self.findtext(rootelement,"availabilityZone")
            create_time = self.findtext(rootelement,"createTime")
            lines.append(["VOLUME", volumeId, size, availability_zone, status, create_time])
            lines.extend(self.parseAttachmentSet(rootelement))
        return lines

    
class GetConsoleOutputResponse(Response):
    def parse(self):
        doc = ET.XML(self.http_xml)
        return [ [self.findtext(doc, "instanceId")],
                 [self.findtext(doc, "timestamp")],
                 [self.findtext(doc, "output")] ]


class TerminateInstancesResponse(Response):
    """Response parser class for C{TerminateInstances} API call."""
    ELEMENT_XPATH = "instancesSet/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for element in self.findall(doc, self.ELEMENT_XPATH):
            instanceId = self.findtext(element, "instanceId")
            shutdownState = self.findtext(element, "shutdownState/name")
            previousState = self.findtext(element, "previousState/name")
            # Only for debug mode, which we don't support yet:
            shutdownStateCode = self.findtext(element, "shutdownState/code")
            previousStateCode = self.findtext(element, "previousState/code")
            lines.append(["INSTANCE", instanceId, previousState, shutdownState])
        return lines


class RebootInstancesResponse(Response):
    """Response parser class for C{RebootInstances} API call."""
    def parse(self):
        # If we don't get an error, the creation succeeded.
        return [["Instances rebooted."]]


class CreateSecurityGroupResponse(Response):
    """Response parser class for C{CreateSecurityGroup} API call."""
    def parse(self):
        # If we don't get an error, the creation succeeded.
        return [["Security Group created."]]


class DescribeSecurityGroupsResponse(Response):
    """Response parser class for C{DescribeSecurityGroups} API call."""
    ELEMENT_XPATH = "securityGroupInfo/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for rootelement in self.findall(doc, self.ELEMENT_XPATH):
            groupName = self.findtext(rootelement, "groupName")
            ownerId = self.findtext(rootelement, "ownerId")
            groupDescription = self.findtext(rootelement, "groupDescription")
            lines.append(["GROUP", ownerId, groupName, groupDescription])
            for element in self.findall(rootelement, "ipPermissions/item"):
                ipProtocol = self.findtext(element, "ipProtocol")
                fromPort = self.findtext(element, "fromPort")
                toPort = self.findtext(element, "toPort")
                permList = [
                    "PERMISSION",
                    ownerId,
                    groupName,
                    "ALLOWS",
                    ipProtocol,
                    fromPort,
                    toPort,
                    "FROM"
                    ]
                for subelement in self.findall(element, "groups/item"):
                    userId = self.findtext(subelement, "userId")
                    targetGroupName = self.findtext(subelement, "groupName")
                    lines.append(permList + ["USER", userId, "GRPNAME", targetGroupName])
                for subelement in self.findall(element, "ipRanges/item"):
                    cidrIp = self.findtext(subelement, "cidrIp")
                    lines.append(permList + ["CIDR", cidrIp])
        return lines


class DeleteSecurityGroupResponse(Response):
    """Response parser class for C{DeleteSecurityGroup} API call."""
    def parse(self):
        # If we don't get an error, the deletion succeeded.
        return [["Security Group deleted."]]


class AuthorizeSecurityGroupIngressResponse(Response):
    """Response parser class for C{AuthorizeSecurityGroupIngress} API call."""
    def parse(self):
        # If we don't get an error, the authorization succeeded.
        return [["Ingress authorized."]]


class RevokeSecurityGroupIngressResponse(Response):
    """Response parser class for C{RevokeSecurityGroupIngress} API call."""
    def parse(self):
        # If we don't get an error, the revocation succeeded.
        return [["Ingress revoked."]]


class ModifyImageAttributeResponse(Response):
    """Response parser class for C{ModifyImageAttribute} API call."""
    def parse(self):
        # If we don't get an error, modification succeeded.
        return [["Image attribute modified."]]


class ResetImageAttributeResponse(Response):
    """Response parser class for C{ResetImageAttribute} API call."""
    def parse(self):
        # If we don't get an error, reset succeeded.
        return [["Image attribute reset."]]


class DescribeImageAttributeResponse(Response):
    """Response parser class for C{DescribeImageAttribute} API call."""
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []

        imageId = self.findtext(doc, "imageId")

        # Handle launchPermission attributes:
        element = self.find(doc, "launchPermission/item")
        if element != None:
            for subelement in element.getchildren():
                lines.append([
                    "launchPermission",
                    imageId,
                    subelement.tag.split("}")[1],
                    subelement.text
                    ])
        
        # Handle launchPermission attributes:
        element = self.find(doc, "productCodes/item")
        if element != None:
            for subelement in element.getchildren():
                lines.append([
                    "productCode",
                    imageId,
                    subelement.text
                    ])
        
        return lines

class AllocateAddressResponse(Response):
    """Response parser class for C{AllocateAddress} API call."""
    def parse(self):
        doc = ET.XML(self.http_xml)
        publicIp = self.findtext(doc, "publicIp")
        return [["ADDRESS", publicIp]]

class DescribeAddressesResponse(Response):
    """Response parser class for C{DescribeAddresses} API call."""
    ELEMENT_XPATH = "addressesSet/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for element in self.findall(doc, self.ELEMENT_XPATH):
            publicIp = self.findtext(element, "publicIp")
            instanceId = self.findtext(element, "instanceId")
            lines.append(["ADDRESS", publicIp, instanceId])
        return lines

class ReleaseAddressResponse(Response):
    """Response parser class for C{ReleaseAddress} API call."""
    def parse(self):
        # If we don't get an error, reset succeeded.
        return [["Address released."]]

class AssociateAddressResponse(Response):
    """Response parser class for C{AssociateAddress} API call."""
    def parse(self):
        # If we don't get an error, reset succeeded.
        return [["Address associated."]]

class DisassociateAddressResponse(Response):
    """Response parser class for C{DisassociateAddress} API call."""
    def parse(self):
        # If we don't get an error, reset succeeded.
        return [["Address disassociated."]]

class ConfirmProductInstanceResponse(Response):
    """Response parser class for C{ConfirmProductInstance} API call."""
    def parse(self):
        doc = ET.XML(self.http_xml)
        result = self.findtext(doc, "result")
        lines = [[result]]
        if result == "true":
            lines[0].append(self.findtext(doc, "ownerId"))

class DescribeAvailabilityZonesResponse(Response):
    """Response parser class for C{DescribeAvailabilityZones} API call."""
    ELEMENT_XPATH = "availabilityZoneInfo/item"
    def parse(self):
        doc = ET.XML(self.http_xml)
        lines = []
        for element in self.findall(doc, self.ELEMENT_XPATH):
            zoneName = self.findtext(element, "zoneName")
            zoneState = self.findtext(element, "zoneState")
            lines.append(["AVAILABILITYZONE", zoneName, zoneState])
        return lines
