#!/usr/bin/env python
import os
import sys
import glob

import pep8
from pyflakes.scripts import pyflakes


def findpy(path):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for py in findpy(cfile):
                yield py
        if cfile.endswith('.py'):
            yield cfile


def check_pyflakes(srcdir):
    print(">>> Running pyflakes...")
    clean = True
    for pyfile in findpy(srcdir):
        if pyflakes.checkPath(pyfile) != 0:
            clean = False
    return clean


def check_pep8(srcdir):
    print(">>> Running pep8...")
    clean = True
    pep8.process_options([''])
    pep8.options.repeat=True
    for pyfile in findpy(srcdir):
        if pep8.Checker(pyfile).check_all() != 0:
            clean = False
    return clean


def main():
    src = os.path.join(os.path.dirname(sys.argv[0]), 'starcluster')
    if not check_pyflakes(src):
        print
        err = "ERROR: pyflakes failed on some source files\n"
        err += "ERROR: please fix the errors and re-run this script"
        print(err)
    elif not check_pep8(src):
        print
        err = "ERROR: pep8 failed on some source files\n"
        err += "ERROR: please fix the errors and re-run this script"
        print(err)
    else:
        print(">>> Clean!")

if __name__ == '__main__':
    main()
