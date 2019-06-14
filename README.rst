==========================
vsh
==========================

.. image:: http://img.shields.io/badge/license-MIT-brightgreen.svg
    :target: http://opensource.org/licenses/MIT

.. image:: https://badge.fury.io/py/vsh.svg
    :target: https://pypi.python.org/pypi/vsh

.. image:: https://travis-ci.org/brianbruggeman/vsh.svg
    :target: https://travis-ci.org/brianbruggeman/vsh


A virtual environment shell


Motivation
----------

I was inspired by vex and pew to create a shell environment; I think
that was the correct approach, but I wanted to extend the tool without
any bureaucracy or red tape.  Some of these choices could alienate the
general community, so this is its own project.

* Python 3.7+
* Even more streamlined command-line interface
* Production installation setting compatible with something like Ansible
* Even better control on environment:
    - executes scripts (bash, python, other) upon startup (DONE) and teardown (TODO)
    - change environment variables
* An easy way to embed vsh as a library (See: `vsh/api.py <https://github.com/brianbruggeman/vsh/tree/master/vsh/api.py>`_)
* Something that actually worked on windows
* No external dependencies (But see: `vsh/vendored <https://github.com/brianbruggeman/vsh/tree/master/vsh/vendored>`_)


Installation
------------
To install vsh, simply::

    $ pip install vsh


Documentation
-------------

Quickstart
^^^^^^^^^^

Enter or Create and enter a new virtual environment::

    $ vsh VenvName
    (VenvName) $

Remove a previously created virtual environment::

    $ vsh -r VenvName

Create an ephemeral virtual environment::

    $ vsh -e VenvName


To set a working folder for each subsequent vsh invocation::

    $ vsh -w /path/to/my/repo VenvName
    /path/to/my/repo (VenvName)$ exit

    $ vsh VenvName
    /path/to/my/repo (VenvName)$ ...

More Commands
^^^^^^^^^^^^^

See Command Reference


Environment Variables
---------------------

The following environment variables are used:

+---------------+--------------------+--------------------------------+
| Name          | Default            | Description                    |
+===============+====================+================================+
| HOME          | $HOME              | Defines user's home (system)   |
+---------------+--------------------+--------------------------------+
| PATH          | $PATH              | Defines executable locations   |
+---------------+--------------------+--------------------------------+
| PROMPT        | $PROMPT            | ZSH prompt variable            |
+---------------+--------------------+--------------------------------+
| PS1           | $PS1               | BASH/SH prompt variable        |
+---------------+--------------------+--------------------------------+
| SHELL         | $SHELL             | Shell identification           |
+---------------+--------------------+--------------------------------+
| WORKON_HOME   | $HOME/.virtualenvs | default, single path for venvs |
+---------------+--------------------+--------------------------------+

For more detail, see: `vsh/env.py <https://github.com/brianbruggeman/vsh/tree/master/vsh/env.py>`_


Development
-----------

To quickly startup in development mode, clone the source code from Github::

    $ git clone https://github.com/brianbruggeman/vsh.git vsh

Create and activate a virtual environment::

    $ python3 -m venv $WORKON_HOME/vsh
    $ $WORKON_HOME/vsh/bin/activate

Install vsh in development mode::

    (vsh) $ cd vsh && pip install -e .[all]

Run the tests to verify that the setup is complete (and the tests pass)::

    (vsh) $ pytest --cache-clear

Please feel free to submit pull requests and file bugs using the
issue tracker.

.. _api: https://github.com/brianbruggeman/vsh/tree/master/vsh/api.py
