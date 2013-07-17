# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

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
