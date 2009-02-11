#!/usr/bin/env python
import os
import ConfigParser

"""
Reads all variables defined in .molsimcfg config file into molsimcfg module's namespace
"""

config = ConfigParser.ConfigParser()
config.read(os.path.expanduser('~/.molsimcfg'))

for section in config.sections():
    for option in config.options(section):
        globals()[option.upper()] = config.get(section,option)

DEFAULT_CLUSTER_SIZE=int(DEFAULT_CLUSTER_SIZE)
