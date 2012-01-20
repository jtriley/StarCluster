from completers import InstanceCompleter


class CmdShowConsole(InstanceCompleter):
    """
    showconsole <instance-id>

    Show console output for an EC2 instance

    Example:

        $ starcluster showconsole i-999999

    This will display the startup logs for instance i-999999
    """
    names = ['showconsole', 'sc']

    def execute(self, args):
        if not len(args) == 1:
            self.parser.error('please provide an instance id')
        instance_id = args[0]
        self.ec2.show_console_output(instance_id)
