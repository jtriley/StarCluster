from os.path import expanduser

from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log
 
class AWSUserCredentialsPlugin(ClusterSetup):
    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Copying AWS credentials for ec2-user")
        aws_credentials = expanduser("~") + "/.aws/config"
        user_credentials = expanduser("~") + "/.ssh/id_rsa"

        master.ssh.execute("mkdir /root/.aws/")
        master.ssh.put(aws_credentials, "/root/.aws")
        master.ssh.execute("mkdir /home/ec2-user/.aws/")
        master.ssh.execute("cp /root/.aws/config /home/ec2-user/.aws/")
        master.ssh.execute("chown -R ec2-user:ec2-user /home/ec2-user/.aws")

        master.ssh.put(user_credentials, "/home/ec2-user/.ssh/")
        master.ssh.execute("chown ec2-user:ec2-user /home/ec2-user/.ssh/id_rsa")
