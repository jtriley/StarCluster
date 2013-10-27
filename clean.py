#!/usr/bin/env python
import os
import glob


def find_cruft(path, extensions=['.pyc', '.pyo']):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for cruft in find_cruft(cfile):
                yield cruft
        fname, ext = os.path.splitext(cfile)
        if ext in extensions:
            yield cfile


def main():
    repo_root = os.path.dirname(__file__)
    sc_src = os.path.join(repo_root, 'starcluster')
    for i in find_cruft(sc_src):
        os.unlink(i)
    for i in glob.glob('*.pyc'):
        os.unlink(i)

if __name__ == '__main__':
    main()
