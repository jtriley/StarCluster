###########################
Using StarCluster Git Hooks
###########################
To enable StarCluster's git hooks that perform PEP8 formatting and pyflakes
validation prior to committing::

1. Check out the StarCluster repo::

    $ git clone https://github.com/jtriley/StarCluster.git

2. Next change the current working directory to the root of the repo::

    $ cd StarCluster

3. Make symbolic links to the hooks in your ``<repo>/.git/hooks`` directory::

    $ ln -s $PWD/git-hooks/pre-commit $PWD/.git/hooks/pre-commit

4. Install both ``pep8`` and ``pyflakes`` packages from PYPI::

    $ easy_install pep8 pyflakes

Now whenever you run ``git commit`` both PEP8 and PyFlakes will check the files
to be committed for errors, e.g.::

    $ git commit
    >>> Running pyflakes...
    starcluster/awsutils.py:333: undefined name 'blah'
    ERROR: pyflakes failed on some source files
    ERROR: please fix the errors and re-run this script
