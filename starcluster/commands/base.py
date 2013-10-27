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
import sys
import time

from starcluster import node
from starcluster import cluster
from starcluster import completion
from starcluster.logger import log


class CmdBase(completion.CmdComplete):
    """
    Base class for StarCluster commands

    Each command consists of a class, which has the following properties:

    - Must have a class member 'names' which is a list of the names for
    the command

    - Can optionally define an addopts(self, parser) method which adds options
    to the given parser. This defines the command's options.
    """
    parser = None
    opts = None
    gopts = None
    gparser = None
    subcmds_map = None
    _cfg = None
    _ec2 = None
    _s3 = None
    _cm = None
    _nm = None

    @property
    def comp_words(self):
        """
        Property that returns COMP_WORDS from Bash/Zsh completion
        """
        return os.environ.get('COMP_WORDS', '').split()

    @property
    def goptions_dict(self):
        """
        Returns global options dictionary
        """
        return dict(getattr(self.gopts, '__dict__', {}))

    @property
    def options_dict(self):
        """
        Returns dictionary of options for this command
        """
        return dict(getattr(self.opts, '__dict__', {}))

    @property
    def specified_options_dict(self):
        """
        Return only those options with a non-None value
        """
        specified = {}
        options = self.options_dict
        for opt in options:
            if options[opt] is not None:
                specified[opt] = options[opt]
        return specified

    @property
    def log(self):
        return log

    @property
    def cfg(self):
        """
        Get global StarClusterConfig object
        """
        if not self._cfg:
            self._cfg = self.goptions_dict.get('CONFIG')
        return self._cfg

    @property
    def ec2(self):
        """
        Get EasyEC2 object from config and connect to the region specified
        by the user in the global options (if any)
        """
        if not self._ec2:
            ec2 = self.cfg.get_easy_ec2()
            if self.gopts.REGION:
                ec2.connect_to_region(self.gopts.REGION)
            self._ec2 = ec2
        return self._ec2

    @property
    def cluster_manager(self):
        """
        Returns ClusterManager object configured with self.cfg and self.ec2
        """
        if not self._cm:
            cm = cluster.ClusterManager(self.cfg, ec2=self.ec2)
            self._cm = cm
        return self._cm

    cm = cluster_manager

    @property
    def node_manager(self):
        """
        Returns NodeManager object configured with self.cfg and self.ec2
        """
        if not self._nm:
            nm = node.NodeManager(self.cfg, ec2=self.ec2)
            self._nm = nm
        return self._nm

    nm = node_manager

    @property
    def s3(self):
        if not self._s3:
            self._s3 = self.cfg.get_easy_s3()
        return self._s3

    def addopts(self, parser):
        pass

    def cancel_command(self, signum, frame):
        """
        Exits program with return value of 1
        """
        print
        log.info("Exiting...")
        sys.exit(1)

    def warn_experimental(self, msg, num_secs=10):
        """
        Warn user that an experimental feature is being used
        Counts down from num_secs before continuing
        """
        sep = '*' * 60
        log.warn('\n'.join([sep, msg, sep]), extra=dict(__textwrap__=True))
        r = range(1, num_secs + 1)
        r.reverse()
        print
        log.warn("Waiting %d seconds before continuing..." % num_secs)
        log.warn("Press CTRL-C to cancel...")
        for i in r:
            sys.stdout.write('%d...' % i)
            sys.stdout.flush()
            time.sleep(1)
        print

    def _positive_int(self, option, opt_str, value, parser):
        if value <= 0:
            parser.error("option %s must be a positive integer" % opt_str)
        setattr(parser.values, option.dest, value)

    def _build_dict(self, option, opt_str, value, parser):
        tagdict = getattr(parser.values, option.dest)
        tags = value.split(',')
        for tag in tags:
            tagparts = tag.split('=')
            key = tagparts[0]
            if not key:
                continue
            value = None
            if len(tagparts) == 2:
                value = tagparts[1]
            tagstore = tagdict.get(key)
            if isinstance(tagstore, basestring) and value:
                tagstore = [tagstore, value]
            elif isinstance(tagstore, list) and value:
                tagstore.append(value)
            else:
                tagstore = value
            tagdict[key] = tagstore
        setattr(parser.values, option.dest, tagdict)
