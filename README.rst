==========================
vesty
==========================

A virtual environment shell


Motivation
----------

Note: Vesty was ves but the name was taken on May 2, 2017.  Consequently,
the package is named vesty, but command-line interface is still `ves`

I was inspired by vex and pew to create a shell environment; I think
that was the correct approach, but I wanted to extend the tool without
any beauracracy or red tape.  Some of these choices could alienate the
general community, so this is its own project.

* Python 3.6+
* Even more streamlined command-line interface
* Production installation setting compatible with something like Ansible
* Even better control on environment:
    - executes scripts (bash, python, other) upon startup and teardown
    - change environment variables


Installation
------------
To install ves, simply::

    $ pip install vesty


Documentation
-------------

Quickstart
^^^^^^^^^^

Enter or Create and enter a new virtual environment::

    $ ves VenvName
    (VenvName) $

Remove a previously created virtual environment::

    $ ves -r VenvName

Create an ephemeral virtual environment::

    $ ves -e VenvName


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

    $ git clone https://github.com/brianbruggeman/ves.git ves

Create and activate a virtual environment::

    $ python3 -m venv $WORKON_HOME/ves
    $ $WORKON_HOME/ves/bin/activate

Install ves in development mode::

    (ves) $ cd ves && pip install -e .[all]

Run the tests to verify that the setup is complete (and the tests pass)::

    (ves) $ pytest --cache-clear

Please feel free to submit pull requests and file bugs using the
issue tracker.
