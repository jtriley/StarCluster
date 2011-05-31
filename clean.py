#!/usr/bin/env python
import os
import sys
import glob

def find_cruft(path, extensions=['.pyc', '.pyo']):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            find_cruft(cfile)
        fname, ext = os.path.splitext(cfile)
        if ext in extensions:
            yield cfile

def main():
    sc_src=os.path.join(os.path.dirname(sys.argv[0]), 'starcluster')
    for i in find_cruft(sc_src):
        os.unlink(i)

if __name__ == '__main__':
    main()
