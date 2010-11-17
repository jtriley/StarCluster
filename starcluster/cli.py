#!/usr/bin/env python
"""
StarCluster Command Line Interface:

starcluster [global-opts] action [action-opts] [<action-args> ...]
"""

import os
import sys
import socket
import optparse

# hack for now to ignore paramiko 1.7.6 using RandomPool (report bug)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from boto.exception import BotoServerError, EC2ResponseError, S3ResponseError

from starcluster import config
from starcluster import static
from starcluster import exception
from starcluster import optcomplete
from starcluster.commands import all_cmds
from starcluster.logger import log, console, DEBUG

from starcluster import __version__

__description__ = """
StarCluster - (http://web.mit.edu/starcluster) (v. %s)
Software Tools for Academics and Researchers (STAR)
Please submit bug reports to starcluster@mit.edu
""" % __version__


class StarClusterCLI(object):
    """
    StarCluster Command Line Interface
    """

    gparser = None
    subcmds_map = {}

    def get_description(self):
        return __description__.replace('\n', '', 1)

    def parse_subcommands(self, gparser, subcmds):
        """
        Parse given global arguments, find subcommand from given list of
        subcommand objects, parse local arguments and return a tuple of
        global options, selected command object, command options, and
        command arguments.

        Call execute() on the command object to run. The command object has
        members 'gopts' and 'opts' set for global and command options
        respectively, you don't need to call execute with those but you could
        if you wanted to.
        """
        print self.get_description()

        # Build map of name -> command and docstring.
        cmds_header = 'Available Commands:'
        gparser.usage += '\n\n%s\n' % cmds_header
        gparser.usage += '%s\n' % ('-' * len(cmds_header))
        gparser.usage += "NOTE: Pass --help to any command for a list of its "
        gparser.usage += 'options and detailed usage information\n\n'
        for sc in subcmds:
            helptxt = sc.__doc__.splitlines()[3].strip()
            gparser.usage += '- %s: %s\n' % (', '.join(sc.names),
                                           helptxt)
            for n in sc.names:
                assert n not in self.subcmds_map
                self.subcmds_map[n] = sc

        # Declare and parse global options.
        gparser.disable_interspersed_args()

        gopts, args = gparser.parse_args()
        if not args:
            gparser.print_help()
            raise SystemExit("\nError: you must specify an action.")
        subcmdname, subargs = args[0], args[1:]

        # set debug level if specified
        if gopts.DEBUG:
            console.setLevel(DEBUG)
        # load StarClusterConfig into global options
        try:
            cfg = config.StarClusterConfig(gopts.CONFIG)
            cfg.load()
        except exception.ConfigNotFound, e:
            log.error(e.msg)
            e.display_options()
            sys.exit(1)
        except exception.ConfigError, e:
            log.error(e.msg)
            sys.exit(1)
        gopts.CONFIG = cfg

        # Parse command arguments and invoke command.
        try:
            sc = self.subcmds_map[subcmdname]
            lparser = optparse.OptionParser(sc.__doc__.strip())
            sc.addopts(lparser)
            sc.parser = lparser
            sc.gparser = self.gparser
            sc.subcmds_map = self.subcmds_map
            sc.gopts = gopts
            sc.opts, subsubargs = lparser.parse_args(subargs)
        except KeyError:
            raise SystemExit("Error: invalid command '%s'" % subcmdname)
        return gopts, sc, sc.opts, subsubargs

    def create_global_parser(self):
        gparser = optparse.OptionParser(__doc__.strip(), version=__version__)
        gparser.add_option("-d", "--debug", dest="DEBUG",
                           action="store_true", default=False,
                           help="print debug messages " + \
                           "(useful for diagnosing problems)")
        gparser.add_option("-c", "--config", dest="CONFIG", action="store",
                           metavar="FILE",
                           help="use alternate config file (default: %s)" % \
                           static.STARCLUSTER_CFG_FILE)
        gparser.add_option("-r", "--region", dest="REGION", action="store",
                           help="specify a region to use instead of the " + \
                           "default (us-east-1)")
        return gparser

    def main(self):
        # Create global options parser.
        self.gparser = gparser = self.create_global_parser()
        # Declare subcommands.
        subcmds = all_cmds
        # subcommand completions
        scmap = {}
        for sc in subcmds:
            for n in sc.names:
                scmap[n] = sc

        if optcomplete:
            listcter = optcomplete.ListCompleter(scmap.keys())
            subcter = optcomplete.NoneCompleter()
            optcomplete.autocomplete(
                gparser, listcter, None, subcter, subcommands=scmap)
        elif 'COMP_LINE' in os.environ:
            return -1

        gopts, sc, opts, args = self.parse_subcommands(gparser, subcmds)
        if args and args[0] == 'help':
            sc.parser.print_help()
            sys.exit(0)
        try:
            sc.execute(args)
        except exception.BaseException, e:
            lines = e.msg.splitlines()
            for l in lines:
                log.error(l)
            sys.exit(1)
        except (EC2ResponseError, S3ResponseError, BotoServerError), e:
            log.error("%s: %s" % (e.error_code, e.error_message))
            sys.exit(1)
        except socket.gaierror, e:
            log.error("Unable to connect: %s" % e)
            log.error("Check your internet connection?")
            sys.exit(1)
        except SystemExit, e:
            raise e
        except Exception, e:
            import traceback
            if not gopts.DEBUG:
                traceback.print_exc()
            log.debug(traceback.format_exc())
            print
            log.error("Oops! Looks like you've found a bug in StarCluster")
            log.error("Debug file written to: %s" % static.DEBUG_FILE)
            log.error(
                "Please submit this file, minus any private information,")
            log.error("to starcluster@mit.edu")
            sys.exit(1)


def main():
    StarClusterCLI().main()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "Interrupted, exiting."
