import optparse

from base import CmdBase


class CmdHelp(CmdBase):
    """
    help

    Show StarCluster usage
    """
    names = ['help']

    def execute(self, args):
        if args:
            cmdname = args[0]
            try:
                sc = self.subcmds_map[cmdname]
                lparser = optparse.OptionParser(sc.__doc__.strip())
                if hasattr(sc, 'addopts'):
                    sc.addopts(lparser)
                lparser.print_help()
            except KeyError:
                raise SystemExit("Error: invalid command '%s'" % cmdname)
        else:
            self.gparser.parse_args(['--help'])
