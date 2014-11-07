import subprocess

from starcluster import clustersetup
from starcluster.logger import log

class GitCredentials(clustersetup.DefaultClusterSetup):
    """
    This plugin installs a user's Git credentials on the master node.

    ##################
    # EXAMPLE CONFIG #
    ##################
    [plugin gitcredentials]
    setup_class = starcluster.plugins.git.GitCredentials

    # this is a private SSH key, the public half of which you have already added to your github account
    private_github_ssh_key_location = /Users/kevin/.ssh/new_id_rsa

    # user name and email address you want set on the master
    git_user_name = "Kevin Bache"
    git_user_email = "kevin.bache@gmail.com"

    # comma separated list of repos which should each be updated to current with a git pull command on the master node
    # note that this only happens on the master node, not all nodes in the cluster.  this is based on the assumption
    # that your repos will be made available to the worker nodes via NFS from the master
    locations_of_remote_repos_to_pull = /code/eyes_open/, /home/sgeadmin/path/to/my/existing/repo/

    """

    USERNAME_COMMAND = 'git config --global user.name \"%s\"'
    EMAIL_COMMAND = 'git config --global user.email \"%s\"'

    SSH_CONFIG_ADDON = """
Host github.com
 IdentityFile ~/.ssh/%s
"""

    def __init__(self,
                 private_github_ssh_key_location=None,
                 git_user_name=None,
                 git_user_email=None,
                 locations_of_remote_repos_to_pull=None):
        super(GitCredentials, self).__init__()
        self.key_location = private_github_ssh_key_location
        self.git_user_name = git_user_name
        self.git_user_email = git_user_email
        self.repos = locations_of_remote_repos_to_pull
        if locations_of_remote_repos_to_pull:
            self.repos = [repo.strip() for repo in locations_of_remote_repos_to_pull.split(',')]

    def run(self, nodes, master, user, user_shell, volumes):
        # add local ssh rsa key to master node for GitHub access
        if not self.key_location:
            log.info("GitCredentials: No GitHub SSH key specified!")
        else:
            log.info("GitCredentials: Using SSH Agent forwarding to share key in %s for Git pulls " % self.key_location)
            # username = 'root'
            # user = master.getpwnam(username)
            # ssh_folder = posixpath.join(user.pw_dir, '.ssh')

            # add SSH key to local ssh-agent so it can be forwarded later when we call the pull commands.
            print 'KEVINPRINT about to run eval ssh-agent'
            out = 0
            out += subprocess.call('eval `ssh-agent -s`', shell=True)
            print 'KEVINPRINT about to run ssh-add'
            out += subprocess.call('ssh-add %s' % self.key_location, shell=True)
            if out:
                raise SystemError("There was a problem adding the key from %s. Does it exist?" % self.key_location)
            print 'KEVINPRINT phew! made it'


            # NOTE: I can't seem to get this ssh-add method to work.  Added keys seem to disappear by your next session.
            # I'm not sure why it seems to persist when I do this on my laptop and seems not to on the cluster but for
            # now I'm just abandoning the whole approach.  On to agent forwarding!
            #
            # # copy private key to master node
            # master.ssh.put(self.key_location, ssh_folder)
            #
            # # tell ssh to always use this key for github.com
            # key_name = os.path.basename(self.key_location)
            # # this ssh-add based solution doesn't seem to work.  it seems to lose the ssh-agent between each shell session
            # # print master.ssh.execute('exec ssh-agent bash && ssh-add ~/.ssh/%s' % key_name)
            # # SOLUTION: ssh-agent/ssh-add the necessary keys on host laptop.  use agent forwarding when sshing in to
            # # git pull
            # print 'key_name:', key_name
            # print 'MONSTER:', 'echo %s >> ~/.ssh/config' % self.SSH_CONFIG_ADDON % key_name
            # print 'ENDMONSTER'
            # master.ssh.execute('echo %s >> ~/.ssh/config' % self.SSH_CONFIG_ADDON % key_name)
            # print master.ssh.execute('')

        # set git user name
        if not self.git_user_name:
            log.info("GitCredentials: No GitHub user name specified!")
        else:
            log.info("GitCredentials: Setting GitHub user name on master node to %s" % self.git_user_name)
            master.ssh.execute(self.USERNAME_COMMAND % self.git_user_name)

        # set git email address
        if not self.git_user_email:
            log.info("GitCredentials: No GitHub user email specified!")
        else:
            log.info("GitCredentials: Setting GitHub user email on master node to %s" % self.git_user_name)
            master.ssh.execute(self.EMAIL_COMMAND % self.git_user_email)

        # pull remote git repos
        if not self.repos:
            log.info("GitCredentials: No remote repositories to pull!")
        else:
            log.info("GitCredentials: Setting GitHub user name on master node to %s" % self.git_user_name)
            for repo in self.repos:
                log.info("GitCredentials: Pulling repo at %s" % repo)
                master.shell(user='root', command='cd %s && git pull' % repo, forward_agent=True)
                # master.ssh.execute('cd %s' % repo)
                # master.ssh.execute('git pull')
