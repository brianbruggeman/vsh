# -*- coding: utf-8 -*-
"""
    pygments.lexers.text
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for non-source code file types.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from vsh.vendored.pygments.lexers.configs import ApacheConfLexer, NginxConfLexer, \
    SquidConfLexer, LighttpdConfLexer, IniLexer, RegeditLexer, PropertiesLexer
from vsh.vendored.pygments.lexers.console import PyPyLogLexer
from vsh.vendored.pygments.lexers.textedit import VimLexer
from vsh.vendored.pygments.lexers.markup import BBCodeLexer, MoinWikiLexer, RstLexer, \
    TexLexer, GroffLexer
from vsh.vendored.pygments.lexers.installers import DebianControlLexer, SourcesListLexer
from vsh.vendored.pygments.lexers.make import MakefileLexer, BaseMakefileLexer, CMakeLexer
from vsh.vendored.pygments.lexers.haxe import HxmlLexer
from vsh.vendored.pygments.lexers.diff import DiffLexer, DarcsPatchLexer
from vsh.vendored.pygments.lexers.data import YamlLexer
from vsh.vendored.pygments.lexers.textfmts import IrcLogsLexer, GettextLexer, HttpLexer

__all__ = []
