class Validator(object):
    """
    Base class for all validating classes
    """
    def validate(self):
        """
        Raises an exception if any validation tests fail
        """
        pass

    def is_valid(self):
        """
        Returns False if any validation tests fail, otherwise returns True
        """
        pass
