#!/usr/bin/env python
import os
import re
import sys
import glob
import subprocess

import pep8
from pyflakes.scripts import pyflakes


CHECKS = [
    #{
        #'start_msg': 'Running Pyflakes...',
        #'command': 'pyflakes %s',
        #'match_files': ['.*\.py$'],
    #},
    #{
        #'start_msg': 'Running pep8...',
        #'command': 'pep8 -r %s',
        #'match_files': ['.*\.py$'],
    #},
]


def matches_file(file_name, match_files):
    return any(re.compile(match_file).match(file_name) for match_file in
               match_files)


def check_files(files, check):
    clean = True
    print check['start_msg']
    for file_name in files:
        if not matches_file(file_name, check.get('match_files', [])):
            continue
        if matches_file(file_name, check.get('ignore_files', [])):
            continue
        print 'checking file: %s' % file_name
        process = subprocess.Popen(check['command'] % file_name,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        output = out + err
        if output:
            output_lines = ['%s: %s' % (file_name, line) for line in
                            (out + err).splitlines()]
            print '\n'.join(output_lines)
        if process.returncode != 0:
            clean = False
    if not clean:
        raise Exception("ERROR: checks failed on some source files")


def check_commands(files):
    for check in CHECKS:
        check_files(files, check)


def find_py_files(path):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for py in find_py_files(cfile):
                yield py
        if cfile.endswith('.py'):
            yield cfile


def check_pyflakes(files):
    print(">>> Running pyflakes...")
    clean = True
    for pyfile in files:
        if pyflakes.checkPath(pyfile) != 0:
            clean = False
    if not clean:
        raise Exception("ERROR: pyflakes failed on some source files")


def check_pep8(files):
    print(">>> Running pep8...")
    clean = True
    pep8.process_options([''])
    pep8.options.repeat = True
    for pyfile in files:
        if pep8.Checker(pyfile).check_all() != 0:
            clean = False
    if not clean:
        raise Exception("ERROR: pep8 failed on some source files")


def main(git_index=False, filetypes=['.py']):
    files = []
    if git_index:
        p = subprocess.Popen(['git', 'status', '--porcelain'],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        modified = re.compile('^(?:MM|M|A)(\s+)(?P<name>.*)')
        for line in out.splitlines():
            match = modified.match(line)
            if match:
                f = match.group('name')
                if filetypes:
                    if f.endswith(tuple(filetypes)):
                        files.append(f)
                else:
                    files.append(f)
    else:
        src = os.path.join(os.path.dirname(__file__), 'starcluster')
        files = find_py_files(src)
    if not files:
        return
    try:
        check_pyflakes(files)
        check_pep8(files)
        print(">>> Clean!")
    except Exception, e:
        print
        print(e)
        print("ERROR: please fix the errors and re-run this script")
        sys.exit(1)

if __name__ == '__main__':
    git_index = '--git-index' in sys.argv
    main(git_index=git_index)
