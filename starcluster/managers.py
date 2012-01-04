class Manager(object):
    """
    Base class for all Manager classes in StarCluster
    """
    def __init__(self, cfg, ec2=None):
        self.cfg = cfg
        self.ec2 = ec2 or cfg.get_easy_ec2()
