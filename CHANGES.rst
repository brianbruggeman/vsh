========
VERSIONS
========


0.6.1
-----

- Adds `.vshrc` support

  A `.vshrc` is a bash script that will be sourced at the start of entering a virtual environment.  The use-case for this
  is that environment variables can be set, or extra code can be run (for example bash completion for click).  `.vshrc`
  may be found in any of the following locations:

  - .
  - git rev-parse --show-toplevel
  - $HOME
  - /usr/local/etc/vshrc
  - $WORKON_HOME/$VIRTUALENV_NAME

  `.vshrc` may be a folder or a file.  If it's a folder, there's no guarantee for which file will be executed first.

  Additionally, a .vshrc will be added to the virtual environment on creation.  This file will include a change
  directory to where vsh was first invoked.  This can be modified by updating the created file.
