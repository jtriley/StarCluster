#!/usr/bin/env python
class AttributeDict(dict):
    """ Subclass of dict that allows read-only attribute-like access to
    dictionary key/values"""
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError,e:
            return super(AttributeDict, self).__getattribute__(name)

def print_timing(func):
    def wrapper(*arg, **kargs):
        t1 = time.time()
        res = func(*arg, **kargs)
        t2 = time.time()
        log.info('%s took %0.3f mins' % (func.func_name, (t2-t1)/60.0))
        return res
    return wrapper
