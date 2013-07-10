import os

from starcluster import clustersetup
from starcluster.logger import log


BOTO_CFG_TEMPLATE = """\
[Credentials]
aws_access_key_id = %(aws_access_key_id)s
aws_secret_access_key = %(aws_secret_access_key)s

[Boto]
https_validate_certificates=True
"""


class BotoPlugin(clustersetup.ClusterSetup):
    """
    Plugin that configures a ~/.boto file for CLUSTER_USER
    """
    def __init__(self, boto_cfg=None):
        self.boto_cfg = os.path.expanduser(boto_cfg or '') or None

    def run(self, nodes, master, user, shell, volumes):
        mssh = master.ssh
        mssh.switch_user(user)
        botocfg = '/home/%s/.boto' % user
        if not mssh.path_exists(botocfg):
            log.info("Installing AWS credentials for user: %s" % user)
            if self.boto_cfg:
                log.info("Copying %s to %s" % (self.boto_cfg, botocfg))
                mssh.put(self.boto_cfg, botocfg)
            else:
                log.info("Installing current credentials to: %s" % botocfg)
                f = mssh.remote_file(botocfg, 'w')
                f.write(BOTO_CFG_TEMPLATE % master.ec2.__dict__)
                f.close()
            mssh.chmod(0400, botocfg)
        else:
            log.warn("AWS credentials already present - skipping install")
