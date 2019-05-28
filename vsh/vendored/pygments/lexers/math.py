# -*- coding: utf-8 -*-
"""
    pygments.lexers.math
    ~~~~~~~~~~~~~~~~~~~~

    Just export lexers that were contained in this module.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from vsh.vendored.pygments.lexers.python import NumPyLexer
from vsh.vendored.pygments.lexers.matlab import MatlabLexer, MatlabSessionLexer, \
    OctaveLexer, ScilabLexer
from vsh.vendored.pygments.lexers.julia import JuliaLexer, JuliaConsoleLexer
from vsh.vendored.pygments.lexers.r import RConsoleLexer, SLexer, RdLexer
from vsh.vendored.pygments.lexers.modeling import BugsLexer, JagsLexer, StanLexer
from vsh.vendored.pygments.lexers.idl import IDLLexer
from vsh.vendored.pygments.lexers.algebra import MuPADLexer

__all__ = []
