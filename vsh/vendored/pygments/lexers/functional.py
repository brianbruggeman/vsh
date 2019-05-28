# -*- coding: utf-8 -*-
"""
    pygments.lexers.functional
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Just export lexer classes previously contained in this module.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from vsh.vendored.pygments.lexers.lisp import SchemeLexer, CommonLispLexer, RacketLexer, \
    NewLispLexer, ShenLexer
from vsh.vendored.pygments.lexers.haskell import HaskellLexer, LiterateHaskellLexer, \
    KokaLexer
from vsh.vendored.pygments.lexers.theorem import CoqLexer
from vsh.vendored.pygments.lexers.erlang import ErlangLexer, ErlangShellLexer, \
    ElixirConsoleLexer, ElixirLexer
from vsh.vendored.pygments.lexers.ml import SMLLexer, OcamlLexer, OpaLexer

__all__ = []
