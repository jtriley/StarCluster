import ssh
from logger import log

class Node(object):
    def __init__(self, instance, key_location, alias, user='root'):
        self.instance = instance
        self.key_location = key_location
        self.alias = alias
        self.user = user
        self._ssh = None

    @property
    def ip_address(self):
        return self.instance.ip_address

    @property
    def public_dns_name(self):
        return self.instance.public_dns_name

    @property
    def private_ip_address(self):
        return self.instance.private_ip_address

    @property 
    def private_dns_name(self):
        return self.instance.private_dns_name

    @property
    def id(self):
        return self.instance.id

    def is_master(self):
        return self.alias == "master"

    @property
    def dns_name(self):
        return self.instance.dns_name

    @property
    def state(self):
        return self.instance.state

    def stop(self):
        return self.instance.stop

    def update(self):
        return self.instance.update()

    @property
    def ssh(self):
        if not self._ssh:
            self._ssh = ssh.Connection(self.instance.dns_name,
                                       username=self.user,
                                       private_key=self.key_location)
        return self._ssh

    def __del__(self):
        if self._ssh:
            self._ssh.close()
