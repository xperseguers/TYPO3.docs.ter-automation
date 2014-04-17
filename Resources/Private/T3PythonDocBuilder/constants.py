#! /usr/bin/python
# coding: ascii

"""\
Some common constants of this package.
"""

__version__ = '1.0.1'

# leave your name and notes here:
__history__ = """\

2013-05-26  Martin Bless <martin@mbless.de>
            Initial release.
"""

__copyright__ = """\

Copyright (c), 2011-2013, Martin Bless  <martin@mbless.de>

All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose and without fee or royalty is hereby
granted, provided that the above copyright notice appears in all copies
and that both that copyright notice and this permission notice appear
in supporting documentation or portions thereof, including
modifications, that you make.

THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO
THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,
INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
WITH THE USE OR PERFORMANCE OF THIS SOFTWARE!
"""


WHITESPACECHARS = '\t\n\x0b\x0c\r '

SECTION_UNDERLINERS = list("""=-^"~'#*$`+;.,_/\%&!""")

META_MAPPING = {
    # name lower : (canonical spelling, keep in output?),
    'content-type'   : ('Content-type'  , 0),
    'description'    : ('Description'   , 1),
    'generator'      : ('Generator'     , 0),
    'author'         : ('Author'        , 1),
    'created'        : ('Created'       , 1),
    'changedby'      : ('Changed by'    , 1),
    'changed'        : ('Changed'       , 1),
    'classification' : ('Classification', 1),
    'content-style-type' : ('Content-style-type', 0),
    'keywords'       : ('Keywords'      , 1),
    'author'         : ('Author'        , 1),
    'email'          : ('Email'         , 1),
    'language (en, de, fr, nl, dk, es, ... )' : ('Language'  , 1),
    'resourceloaderdynamicstyles' : ('Resource_Loader_Dynamic_Styles', 0),
    'sdfootnote'     : ('sdfootnote'    , 0),
    'sdendnote'      : ('sdendnote'     , 0),
}

NL = '\n'
CRLF = '\r\n'

CUTTER_MARK_IMAGES = '.. ######CUTTER_MARK_IMAGES######'

class Dummy(object):
    pass

SNIPPETS = Dummy()
SNIPPETS.for_your_information = """\
.. ==================================================
.. FOR YOUR INFORMATION
.. --------------------------------------------------
.. -*- coding: utf-8 -*- with BOM.

"""
SNIPPETS.define_some_textroles = """\
.. ==================================================
.. DEFINE SOME TEXTROLES
.. --------------------------------------------------
.. role::   underline
.. role::   typoscript(code)
.. role::   ts(typoscript)
   :class:  typoscript
.. role::   php(code)

"""

