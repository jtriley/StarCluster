class AttributeDict(dict):
    """ Subclass of dict that allows read-only attribute-like access to
    dictionary key/values"""
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError,e:
            return super(AttributeDict, self).__getattribute__(name)
