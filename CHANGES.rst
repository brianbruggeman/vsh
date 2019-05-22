========
VERSIONS
========


0.7.0
-----
- Adds support for starting path
- Adds support for ignoring a starting path

- Adds `vsh.cfg` support

  * `vsh.cfg` is a `TOML` file that provides a way to more finely control things like:

     + startup folder
     + environment variables

  * the logic for `vsh.cfg` discovery and `.vshrc` is the same

- Adds Windows support

  * Support is preliminary

     + general pip install doesn't always work on Windows (Errno 13)
     + recommended pip install is using pip's `--user` option
     + When using pip's `--user` option, the windows `PATH` must be updated

- Small performance enhancements

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
