==========================
vsh
==========================

.. image:: https://travis-ci.org/brianbruggeman/vsh.svg?branch=develop
    :target: https://travis-ci.org/brianbruggeman/vsh

A virtual environment shell


Motivation
----------

I was inspired by vex and pew to create a shell environment; I think
that was the correct approach, but I wanted to extend the tool without
any bureaucracy or red tape.  Some of these choices could alienate the
general community, so this is its own project.

* Python 3.6+
* Even more streamlined command-line interface
* Production installation setting compatible with something like Ansible
* Even better control on environment:
    - executes scripts (bash, python, other) upon startup and teardown
    - change environment variables


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


More Commands
^^^^^^^^^^^^^

See Command Reference


Environment Variables
---------------------

+---------------+--------------------+--------------------------------+
| Name          | Default            | Description                    |
+===============+====================+================================+
| WORKON_HOME   | $HOME/.virtualenvs | default, single path for venvs |
+---------------+--------------------+--------------------------------+


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
