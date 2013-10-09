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


s3cmd_cfg_TEMPLATE = """\
[default]
access_key = %(aws_access_key_id)s
bucket_location = US
cloudfront_host = cloudfront.amazonaws.com
default_mime_type = binary/octet-stream
delete_removed = False
dry_run = False
enable_multipart = True
encoding = UTF-8
encrypt = False
follow_symlinks = False
force = False
get_continue = False
gpg_command = %(gpg_command)s
gpg_decrypt = %(gpg_command)s -d --verbose --no-use-agent --batch\
 --yes --passphrase-fd %%(passphrase_fd)s -o %%(output_file)s %%(input_file)s
gpg_encrypt = %(gpg_command)s -c --verbose --no-use-agent --batch\
 --yes --passphrase-fd %%(passphrase_fd)s -o %%(output_file)s %%(input_file)s
gpg_passphrase = %(gpg_passphrase)s
guess_mime_type = True
host_base = s3.amazonaws.com
host_bucket = %%(bucket)s.s3.amazonaws.com
human_readable_sizes = False
invalidate_on_cf = False
list_md5 = False
log_target_prefix =
mime_type =
multipart_chunk_size_mb = 15
preserve_attrs = True
progress_meter = True
proxy_host =
proxy_port = 0
recursive = False
recv_chunk = 4096
reduced_redundancy = False
secret_key = %(aws_secret_access_key)s
send_chunk = 4096
simpledb_host = sdb.amazonaws.com
skip_existing = False
socket_timeout = 300
urlencoding_mode = normal
use_https = %(use_https)s
verbosity = WARNING
website_endpoint = http://%%(bucket)s.s3-website-%%(location)s.amazonaws.com/
website_error =
website_index = index.html
"""


class S3CmdPlugin(clustersetup.ClusterSetup):
    """
    Plugin that configures a ~/.s3cfg file for CLUSTER_USER
    """
    def __init__(self, s3cmd_cfg=None, gpg_command='/usr/bin/gpg',
                 gpg_passphrase="", use_https=False):
        self.s3cmd_cfg = os.path.expanduser(s3cmd_cfg or '') or None
        self.config_dict = {}
        self.config_dict["gpg_command"] = gpg_command
        self.config_dict["gpg_passphrase"] = gpg_passphrase
        self.config_dict["use_https"] = use_https

    def run(self, nodes, master, user, shell, volumes):
        self.config_dict["aws_access_key_id"] = master.ec2.aws_access_key_id
        self.config_dict["aws_secret_access_key"] = master.ec2.aws_secret_access_key
        mssh = master.ssh
        mssh.switch_user(user)
        s3cmd_cfg = "/home/%s/.s3cfg" % user
        if not mssh.path_exists(s3cmd_cfg):
            log.info("Configuring s3cmd for user: %s" % user)
            if self.s3cmd_cfg:
                log.info("Copying %s to %s" % (self.s3cmd_cfg, s3cmd_cfg))
                mssh.put(self.s3cmd_cfg, s3cmd_cfg)
            else:
                log.info("Installing new .s3cfg to: %s" % s3cmd_cfg)
                f = mssh.remote_file(s3cmd_cfg, 'w')
                f.write(s3cmd_cfg_TEMPLATE % self.config_dict)
                f.close()
            mssh.chmod(0400, s3cmd_cfg)
        else:
            log.warn("~/.s3cfg file already present - skipping install")
