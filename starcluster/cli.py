#!/usr/bin/env python
"""
starcluster [global-opts] action [action-opts] [<action-args> ...]
"""

from starcluster import __version__
from starcluster import __author__

__description__ = """
StarCluster - (http://web.mit.edu/starcluster) (v. %s)
Software Tools for Academics and Researchers (STAR)
Please submit bug reports to starcluster@mit.edu
"""  % __version__

__moredoc__ = """
Each command consists of a class, which has the following properties:

- Must have a class member 'names' which is a list of the names for the command;

- Can optionally have a addopts(self, parser) method which adds options to the
  given parser. This defines command options.
"""

import os
import sys
import socket

# hack for now to ignore pycrypto 2.0.1 using md5 and sha
# why is pycrypto 2.1.0 not on pypi?
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from boto.exception import BotoServerError, EC2ResponseError, S3ResponseError

from starcluster import config
from starcluster import static
from starcluster import exception
from starcluster import optcomplete
from starcluster.commands import all_cmds
from starcluster.logger import log, console, DEBUG

#try:
    #import optcomplete
    #CmdComplete = optcomplete.CmdComplete
#except ImportError,e:
    #optcomplete, CmdComplete = None, object

class CmdHelp:
    """
    help

    Show StarCluster usage
    """
    names =['help']
    def execute(self, args):
        import optparse
        if args:
            cmdname = args[0]
            try:
                sc = subcmds_map[cmdname]
                lparser = optparse.OptionParser(sc.__doc__.strip())
                if hasattr(sc, 'addopts'):
                    sc.addopts(lparser)
                lparser.print_help()
            except KeyError:
                raise SystemExit("Error: invalid command '%s'" % cmdname)
        else:
            gparser.parse_args(['--help'])

def get_description():
    return __description__.replace('\n','',1)

def parse_subcommands(gparser, subcmds):

    """Parse given global arguments, find subcommand from given list of
    subcommand objects, parse local arguments and return a tuple of global
    options, selected command object, command options, and command arguments.
    Call execute() on the command object to run. The command object has members
    'gopts' and 'opts' set for global and command options respectively, you
    don't need to call execute with those but you could if you wanted to."""

    import optparse
    global subcmds_map # needed for help command only.

    print get_description()

    # Build map of name -> command and docstring.
    subcmds_map = {}
    gparser.usage += '\n\nAvailable Actions\n'
    for sc in subcmds:
        helptxt = sc.__doc__.splitlines()[3].strip()
        gparser.usage += '- %s: %s\n' % (', '.join(sc.names),
                                       helptxt)
        for n in sc.names:
            assert n not in subcmds_map
            subcmds_map[n] = sc

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
    except exception.ConfigNotFound,e:
        log.error(e.msg)
        e.display_options()
        sys.exit(1)
    except exception.ConfigError,e:
        log.error(e.msg)
        sys.exit(1)
    gopts.CONFIG = cfg

    # Parse command arguments and invoke command.
    try:
        sc = subcmds_map[subcmdname]
        lparser = optparse.OptionParser(sc.__doc__.strip())
        if hasattr(sc, 'addopts'):
            sc.addopts(lparser)
        sc.parser = lparser
        sc.gopts = gopts
        sc.opts, subsubargs = lparser.parse_args(subargs)
    except KeyError:
        raise SystemExit("Error: invalid command '%s'" % subcmdname)

    return gopts, sc, sc.opts, subsubargs

def main():
    # Create global options parser.
    global gparser # only need for 'help' command (optional)
    import optparse
    gparser = optparse.OptionParser(__doc__.strip(), version=__version__)
    gparser.add_option("-d","--debug", dest="DEBUG", action="store_true",
        default=False,
        help="print debug messages (useful for diagnosing problems)")
    gparser.add_option("-c","--config", dest="CONFIG", action="store",
        metavar="FILE",
        help="use alternate config file (default: %s)" % \
                       static.STARCLUSTER_CFG_FILE)

    # Declare subcommands.
    subcmds = all_cmds
    subcmds.append(CmdHelp())
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

    gopts, sc, opts, args = parse_subcommands(gparser, subcmds)
    if args and args[0] =='help':
        sc.parser.print_help()
        sys.exit(0)
    try:
        sc.execute(args)
    except exception.BaseException,e:
        lines = e.msg.splitlines()
        for l in lines:
            log.error(l)
        sys.exit(1)
    except (EC2ResponseError, S3ResponseError, BotoServerError), e:
        log.error("%s: %s" % (e.error_code, e.error_message))
        sys.exit(1)
    except socket.gaierror,e:
        log.error("Unable to connect: %s" % e)
        log.error("Check your internet connection?")
        sys.exit(1)
    except SystemExit,e:
        raise e
    except Exception,e:
        import traceback
        if not gopts.DEBUG:
            traceback.print_exc()
        log.debug(traceback.format_exc())
        print
        log.error("Oops! Looks like you've found a bug in StarCluster")
        log.error("Debug file written to: %s" % static.DEBUG_FILE)
        log.error("Please submit this file, minus any private information,")
        log.error("to starcluster@mit.edu")
        sys.exit(1)

def test():
    pass

if os.environ.has_key('starcluster_commands_test'):
    test()
elif __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "Interrupted, exiting."
