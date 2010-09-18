#!/usr/bin/env python

import os
import sys
import time
import signal
from starcluster import optcomplete
from starcluster.logger import log


class CmdBase(optcomplete.CmdComplete):
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
        return dict(self.gopts.__dict__)

    @property
    def options_dict(self):
        """
        Returns dictionary of options for this command
        """
        return dict(self.opts.__dict__)

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
    def cfg(self):
        """
        Get global StarClusterConfig object
        """
        return self.goptions_dict.get('CONFIG')

    def addopts(self, parser):
        pass

    def cancel_command(self, signum, frame):
        """
        Exits program with return value of 1
        """
        print
        log.info("Exiting...")
        sys.exit(1)

    def catch_ctrl_c(self, handler=None):
        """
        Catch ctrl-c interrupt
        """
        handler = handler or self.cancel_command
        signal.signal(signal.SIGINT, handler)

    def warn_experimental(self, msg, num_secs=10):
        """
        Warn user that an experimental feature is being used
        Counts down from num_secs before continuing
        """
        for l in msg.splitlines():
            log.warn(l)
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
