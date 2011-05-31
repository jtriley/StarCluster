Contributing to StarCluster
===========================
.. note:: 
    **Prequisites**: You need to `install git
    <http://help.github.com/set-up-git-redirect>`_ before following these
    instructions. You should also familiarize yourself with the basic use and
    work flow model of git before following these instructions. The folks over
    at github put together a good `introduction to git <http://gitref.org>`_
    that you can use to get started with git.

Overview
--------

Sign-up for a github acount
---------------------------
StarCluster's source code is stored on `github.com <https://github.com>`_. It is
preferred that you use github.com to submit patches and enhancements via `pull
requests <http://help.github.com/pull-requests/>`_. The first step is to sign
up for a `github account <https://github.com>`_.

Fork the StarCluster project
----------------------------
Once you have a github account the next step is to `fork
<http://help.github.com/fork-a-repo/>`_ the StarCluster github repository. To
do this you must first login to `github <https://github.com>`_ and then
navigate to the `StarCluster repository
<https://github.com/jtriley/StarCluster>`_. Once there click on the **Fork**
button towards the top right of the project page:

.. image:: _static/forkproject.png 

This will create your own copy of the StarCluster repository under your github
account that you can modify and commit to. Having your own copy allows you to
work on bug fixes, docs, new features, etc. without needing special commit
access to the main StarCluster repository.

Clone your fork
---------------
.. code-block::  ini

    $ git clone <user>@github.com:<user>/StarCluster.git

Setup a virtualenv for StarCluster development
----------------------------------------------
When developing a Python project it's useful to work inside an isolated Python
environment that lives inside your *$HOME* folder.  This helps to avoid
dependency version mismatches between projects and also removes the need to
obtain root priviliges to install Python modules/packages for development.

Fortunately there exists a couple of projects that make creating and managing
isolated Python environments quick and easy:

* `virtualenv <http://pypi.python.org/pypi/virtualenv>`_ - Virtual Python Environment builder
* `virtualenvwrapper <http://pypi.python.org/pypi/virtualenvwrapper>`_ - Shell enhancements for virtualenv

To get started you first need to install and configure virtualenv and
virtualenvwrapper:

.. warning::
    You need *root* access to run the *sudo* commands below.

.. code-block::  ini
        
    $ sudo easy_install virtualenv
    $ sudo easy_install virtualenvwrapper
    $ mkdir $HOME/.virtualenvs 
    $ echo "source /usr/local/bin/virtualenvwrapper.sh" >> $HOME/.bashrc

*If* you're using `zsh <http://www.zsh.org>`_ then the last line should be changed to:

.. code-block:: ini

    $ echo "source /usr/local/bin/virtualenvwrapper.sh" >> $HOME/.zshrc

Running these commands will install both virtualenv and virtualenvwrapper and
configure virtualenvwrapper to use **$HOME/.virtualenvs** as the top-level
virtual environment directory where all virtual environments are installed.

At this point you will either need to close your current shell and launch a new
shell or *re-source* your shell's *rc* file:

.. code-block:: ini

    $ source $HOME/.bashrc

This will reload your shell's configuration file and configure
virtualenvwrapper. The next step is to create a new virtual env called
*starcluster* and change into that virtual environment:

.. code-block:: ini

    $ mkvirtualenv --clear --no-site-packages --distribute starcluster

This will create a


Code clean-up
-------------
Before committing any code please be sure to run the `check.py
<https://github.com/jtriley/StarCluster/blob/master/check.py>`_ script in the
root of your StarCluster git repository. This script runs pep8 and pyflakes on
all source files and outputs any errors it finds related to pep8 formatting,
syntax, import errors, undefined variables, etc. Please fix any errors reported
before committing. 

:pep:`8`

.. code-block:: ini

    $ cd $STARCLUSTER_REPO
    $ pip install pep8
    $ pip install pyflakes
    $ ./check.py
    >>> Running pyflakes...
    >>> Running pep8...
    >>> Clean!

Submit your changes upstream
----------------------------
Once you've finished fixing bugs or adding features you're now ready to `submit
a pull request <http://help.github.com/pull-requests/>`_ so that the changes
can be merged upstream and be included in the next stable release.
