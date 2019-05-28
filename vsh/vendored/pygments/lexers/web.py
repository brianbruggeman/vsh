# -*- coding: utf-8 -*-
"""
    pygments.lexers.web
    ~~~~~~~~~~~~~~~~~~~

    Just export previously exported lexers.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from vsh.vendored.pygments.lexers.html import HtmlLexer, DtdLexer, XmlLexer, XsltLexer, \
    HamlLexer, ScamlLexer, JadeLexer
from vsh.vendored.pygments.lexers.css import CssLexer, SassLexer, ScssLexer
from vsh.vendored.pygments.lexers.javascript import JavascriptLexer, LiveScriptLexer, \
    DartLexer, TypeScriptLexer, LassoLexer, ObjectiveJLexer, CoffeeScriptLexer
from vsh.vendored.pygments.lexers.actionscript import ActionScriptLexer, \
    ActionScript3Lexer, MxmlLexer
from vsh.vendored.pygments.lexers.php import PhpLexer
from vsh.vendored.pygments.lexers.webmisc import DuelLexer, XQueryLexer, SlimLexer, QmlLexer
from vsh.vendored.pygments.lexers.data import JsonLexer
JSONLexer = JsonLexer  # for backwards compatibility with Pygments 1.5

__all__ = []
