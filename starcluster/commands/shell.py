#!/usr/bin/env python

import sys

from starcluster import utils
from starcluster.logger import log

from base import CmdBase

class CmdShell(CmdBase):
    """
    shell

    Load interactive IPython shell for starcluster development

    The following objects are automatically available at the prompt:

        cfg - starcluster.config.StarClusterConfig instance
        ec2 - starcluster.awsutils.EasyEC2 instance
        s3 - starcluster.awsutils.EasyS3 instance

    All starcluster modules are automatically imported in the IPython session
    along with the boto and paramiko modules
    """
    names = ['shell', 'sh']
    def execute(self,args):
        cfg = self.cfg
        ec2 = cfg.get_easy_ec2()
        s3 = ec2.s3
        import starcluster
        modules = [ (starcluster.__name__ + '.' + i, i) for i in starcluster.__all__ ] + \
                     [('boto','boto'),('paramiko','paramiko')]
        for fullname, modname in modules:
            log.info('Importing module %s' % modname)
            try:
                __import__(fullname)
                locals()[modname] = sys.modules[fullname]
            except ImportError,e:
                log.error("Error loading module %s: %s" % (modname, e))
        from starcluster.utils import ipy_shell; ipy_shell();
