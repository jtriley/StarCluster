import sys

import starcluster
from starcluster import utils
from starcluster.logger import log

from base import CmdBase


class CmdShell(CmdBase):
    """
    shell

    Load an interactive IPython shell configured for starcluster development

    The following objects are automatically available at the prompt:

        cfg - starcluster.config.StarClusterConfig instance
        ec2 - starcluster.awsutils.EasyEC2 instance
        s3 - starcluster.awsutils.EasyS3 instance

    All starcluster modules are automatically imported in the IPython session
    along with the boto and paramiko modules
    """
    names = ['shell', 'sh']

    def execute(self, args):
        local_ns = dict(cfg=self.cfg, ec2=self.ec2, s3=self.s3, cm=self.cm,
                        starcluster=starcluster)
        modules = [(starcluster.__name__ + '.' + module, module) \
                   for module in starcluster.__all__]
        modules += [('boto', 'boto'), ('paramiko', 'paramiko'),
                    ('workerpool', 'workerpool'), ('jinja2', 'jinja2')]
        for fullname, modname in modules:
            log.info('Importing module %s' % modname)
            try:
                __import__(fullname)
                local_ns[modname] = sys.modules[fullname]
            except ImportError, e:
                log.error("Error loading module %s: %s" % (modname, e))
        utils.ipy_shell(local_ns=local_ns)
