# -*- coding: utf-8 -*-
"""
    pygments.lexers.compiled
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Just export lexer classes previously contained in this module.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from vsh.vendored.pygments.lexers.jvm import JavaLexer, ScalaLexer
from vsh.vendored.pygments.lexers.c_cpp import CLexer, CppLexer
from vsh.vendored.pygments.lexers.d import DLexer
from vsh.vendored.pygments.lexers.objective import ObjectiveCLexer, \
    ObjectiveCppLexer, LogosLexer
from vsh.vendored.pygments.lexers.go import GoLexer
from vsh.vendored.pygments.lexers.rust import RustLexer
from vsh.vendored.pygments.lexers.c_like import ECLexer, ValaLexer, CudaLexer
from vsh.vendored.pygments.lexers.pascal import DelphiLexer, Modula2Lexer, AdaLexer
from vsh.vendored.pygments.lexers.business import CobolLexer, CobolFreeformatLexer
from vsh.vendored.pygments.lexers.fortran import FortranLexer
from vsh.vendored.pygments.lexers.prolog import PrologLexer
from vsh.vendored.pygments.lexers.python import CythonLexer
from vsh.vendored.pygments.lexers.graphics import GLShaderLexer
from vsh.vendored.pygments.lexers.ml import OcamlLexer
from vsh.vendored.pygments.lexers.basic import BlitzBasicLexer, BlitzMaxLexer, MonkeyLexer
from vsh.vendored.pygments.lexers.dylan import DylanLexer, DylanLidLexer, DylanConsoleLexer
from vsh.vendored.pygments.lexers.ooc import OocLexer
from vsh.vendored.pygments.lexers.felix import FelixLexer
from vsh.vendored.pygments.lexers.nimrod import NimrodLexer
from vsh.vendored.pygments.lexers.crystal import CrystalLexer

__all__ = []
