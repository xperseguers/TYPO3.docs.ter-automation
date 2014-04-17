#! /usr/bin/python
# coding: ascii

"""\
Convert an OpenOffice (X)HTML file to reST.
"""

__version__ = '1.2.0'

# leave your name and notes here:
__history__ = """\

2012-03-08  Martin Bless <martin@mbless.de>
            Initial release.
2012-03-10  added: argparse detector
2012-03-11  v1.0.1 ready for git.typo3.org/Documentation/RestTools/oo2rst
2012-03-14  v1.0.2 remove trailing blanks; Bugfix: font_log;
            feature: unique column names; Bugfix: log_comments if taginfo;
            add to: META-MAPPING;
2012-03-15  v1.0.3 Bugfix: superscript etc.; Feature: support for
            textrole underline; Feature: snippets;
2012-03-18  used as is for complete conversion process today
2012-05-20  v1.1.0: Add commandline option 'tables-as'. Mark begin and end
            of tables written as definition lists
2012-05-29  v1.1.1: changed ...
2012-08-29  v1.1.2: write '.. t3-field-list-table::' instead of
            '.. field-list-table::'
2012-08-29  v1.1.3: add option tablesas=t3flt
2013-05-26  v1.2.0: now with import * from constants
"""

__copyright__ = """\

Copyright (c), 2011-2012, Martin Bless  <martin@mbless.de>

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

import codecs
import HTMLParser
from pprint import pprint
import re
import sys

try:
    # cStringIO would be nice but doesn't handle unicode.
    # So we use StringIO in any case.
    from StringIO import StringIO
except ImportError:
    from StringIO import StringIO

from textwrap import TextWrapper

from constants import *

import htmlentitydefs
entitydefs = HTMLParser.entitydefs = {'apos':u"'"}
for k, v in htmlentitydefs.name2codepoint.iteritems():
    entitydefs[k] = unichr(v)


MAIN = Dummy()
MAIN.options = {
    'revealFontTags'        : 0,
    'revealUnderlineTags'   : 0,
    'revealOtherInlineTags' : 0,
}

def myprint(*args, **kwds):
    end  = kwds.get('end', '\n')
    sep  = kwds.get('sep', ' ')
    file = kwds.get('file', sys.stdout)
    for arg in args:
        file.write(arg)
        if sep:
            file.write(sep)
    if end:
        file.write(end)


##  From the Docutils docs:

##  Below is a simplified diagram of the hierarchy of elements in the
##  Docutils document tree structure. An element may contain any other
##  elements immediately below it in the diagram. Notes are written in
##  square brackets. Element types in parentheses indicate recursive or
##  one-to-many relationships; sections may contain (sub)sections, tables
##  contain further body elements, etc.
##
##  +--------------------------------------------------------------------+
##  | document  [may begin with a title, subtitle, decoration, docinfo]  |
##  |                             +--------------------------------------+
##  |                             | sections  [each begins with a title] |
##  +-----------------------------+-------------------------+------------+
##  | [body elements:]                                      | (sections) |
##  |         | - literal | - lists  |       | - hyperlink  +------------+
##  |         |   blocks  | - tables |       |   targets    |
##  | para-   | - doctest | - block  | foot- | - sub. defs  |
##  | graphs  |   blocks  |   quotes | notes | - comments   |
##  +---------+-----------+----------+-------+--------------+
##  | [text]+ | [text]    | (body elements)  | [text]       |
##  | (inline +-----------+------------------+--------------+
##  | markup) |
##  +---------+
##
##  The Docutils document model uses a simple, recursive model for section
##  structure. A document node may contain body elements and section
##  elements. Sections in turn may contain body elements and sections. The
##  level (depth) of a section element is determined from its physical
##  nesting level; unlike other document models (<h1> in HTML, <sect1> in
##  DocBook, <div1> in XMLSpec) the level is not incorporated into the
##  element name.
##
##  The Docutils document model uses strict element content models. Every
##  element has a unique structure and semantics, but elements may be
##  classified into general categories (below). Only elements which are
##  meant to directly contain text data have a mixed content model, where
##  text data and inline elements may be intermixed. This is unlike the much
##  looser HTML document model, where paragraphs and text data may occur at
##  the same level.



class OOHelperFunctions(object):

    def decodeMetaDateAndTime(self, s):
        """
        Examples:
           "20100218;17331800"    - > 2010-02-18 17:33:18 (00)
           "20120222;17525706"    - > 2012-02-22 17:52:57 (06)
           "20120222;17525706987" - > 2012-02-22 17:52:57 (06987)
           "20120222;175257"      - > 2012-02-22 17:52:57 ()
           "20120222;17525"       - > 20120222;17525
        """
        result = s
        if re.match('''\d{8};\d{6}''', s):
            day, tim = s.split(';')
            day = day.strip()
            day = '%s-%s-%s' % (day[:4], day[4:6], day[6:])
            tim = '%s:%s:%s (%s)' % (tim[0:2], tim[2:4], tim[4:6], tim[6:], )
            tim = '%s:%s:%s' % (tim[0:2], tim[2:4], tim[4:6], )
            result = day + ' ' + tim
        return result



class TableDescriptor(object):

    def __init__(self):
        self.col = -1
        self.row = -1
        self.maxcol = -1
        self.maxrow = -1
        self.colnames = []
        self.colwidthsraw = []
        self.colwidths = []
        self.headerrows = 0
        self.theadstatus = '' # '' | 'tbody' | '/tbody'
        self.tbodystatus = '' # '' | 'thead' | '/thead'

    def nextCol(self):
        self.col += 1
        if self.col > self.maxcol:
            self.colnames.append('')
        self.maxcol = max(self.col, self.maxcol)
        return self.col

    def nextRow(self):
        self.row += 1
        self.maxrow = max(self.row, self.maxrow)
        self.col = -1
        return self.row

    def isNewColName(self, s):
        exists = s in self.colnames
        return not exists

    def stringToNewColName(self, s):
        deleteChars = ''.join([chr(i) for i in range(32)])
        deleteChars = deleteChars + ':' + chr(127)
        s = s.encode('latin-1','ignore')
        s = s.strip()
        s = s.translate(None, deleteChars)
        u = s.decode('latin-1')
        if not u:
            stock = 'abcdefghijklmnopqrstuvwxyz0123456789'
            uc = stock[self.col % len(stock)]
            u = uc
            while not self.isNewColName(u):
                u = u + uc
        cnt = 1
        u2 = u
        while not self.isNewColName(u2):
            cnt += 1
            u2 = '%s-%s' % (u, cnt)
        if cnt > 1:
            u = u2
        return u

    def getColName(self, s=''):
        result = None
        if not result:
            result = self.colnames[self.col]
        if not result:
            result = self.stringToNewColName(s)
            self.colnames[self.col] = result
        return result


class DataCollector(object):

    def __init__(self, parent=None, taginfo=0, tablesas='dl'):
        self.parent = parent
        self.taginfo = taginfo
        self.tablesas = tablesas
        self.current_datahandler = None
        self.sbuf = None
        self.stack = []
        self.start_document('initial')
        self.OOHF = OOHelperFunctions()

        # states
        self.verbatim = [False]
        self.is_used_textrole_underline = False
        self.last_src = None

        # intermediate storage
        self.fontstack = []
        self.listsymbolstack = []
        self.dlstack = []
        self.sectionlevel = 0
        self.tablestack = []
        self.collected_images = {}
        self.collected_metas = []

        # write tables as definition lists
        self.stop_table = self.stop_table_AndWrite_neutral
        self.stop_tr = self.stop_tr_AndWrite_definition_list_container
        self.stop_th = self.stop_th_AndWrite_definition_list
        self.stop_td = self.stop_td_AndWrite_definition_list

        if self.tablesas == 'flt' or self.tablesas == 't3flt':
            # write tables as t3-field-list-table directives
            self.stop_table = self.stop_table_AndWrite_field_list_table
            self.stop_tr = self.stop_tr_AndWrite_field_list_table
            self.stop_th = self.stop_th_AndWrite_field_list_table
            self.stop_td = self.stop_td_AndWrite_field_list_table


    def push(self):
        self.stack.append((self.current_datahandler, self.sbuf))

    def pop(self):
        self.current_datahandler, self.sbuf = self.stack.pop()

    def dump(self):
        for i, h, b in enumterate(self.stack):
            print i, h, b

    def collect(self, data, verbatim=None, src=None):
        # think of: self.datacollector.collect(u, src='entityref')
        if verbatim is None:
            verbatim = self.verbatim[-1]
        self.current_datahandler(data, verbatim, src)
        self.last_src = src

    def debuginfo(self, what):
        result = """DataCollector.debuginfo(): don't know how to '%s'""" % what
        if what == 'sbufs':
            L = []
            totalInStack = 0
            for h, sbuf in self.stack:
                if sbuf:
                    L.append(sbuf.tell())
                    totalInStack += sbuf.tell()
            L.append(self.sbuf.tell())
            totalInStack += self.sbuf.tell()
            result = '$($(%s)) %s' % (totalInStack, L)
        return result

    def handle_meta(self, tag, attrs):
        self.collected_metas.append(attrs)

    def handle_img(self, tag, attrs=[]):
        D = {}
        for k,v in attrs:
            D[k] = v
        ## the unit (like 'px') is missing in openoffice html. In this case we append 'px'
        for k in D.keys():
            if k in ['height', 'width']:
                try:
                    int(D[k])
                    D[k] += 'px'
                except ValueError:
                    pass
        src = D['src']
        ci = self.collected_images.get(src,None)
        if ci:
            name, dummyattrs = ci
        else:
            name = 'img-%s' % (len(self.collected_images) + 1)
            self.collected_images[src] = (name, attrs)
        if self.sbuf.tell() and not self.sbuf.getvalue()[-1] in WHITESPACECHARS:
            self.collect(' ', 'verbatim')
        self.collect('|%s| ' % name, 'verbatim')




    def start_document(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_document

    def stop_document(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        return s

    def datahandler_document(self, data, verbatim=None, src=None):
        self.sbuf.write(data)





    def start_html(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_html
        if self.taginfo:
            if attrs:
                self.sbuf.write('.. <%s>   %r\n\n' % (tag, attrs))

    def stop_html(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        self.collect(u'%s\n\n' % s, verbatim=True)

        if self.collected_images:
            self.collect('\n\n', 'verbatim')
            self.collect('%s\n\n' % CUTTER_MARK_IMAGES, 'verbatim')

            if 0:
                print repr(self.collected_images)

            relpath = ''
            # relpath = 'img/'

            name_src = {}
            for src in self.collected_images.keys():
                name, imgattrs = self.collected_images[src]
                name_src[name] = src

            keys = name_src.keys()
            keys = [k[:4] + ('%06d' % int(k[4:])) for k in keys]
            keys = sorted(keys)
            for longname in keys:
                name = longname[:4] + ('%s' % int(longname[4:]))
                src = name_src[name]
                dummy, imgattrs = self.collected_images[src]
                spacer = ' ' * (10-len(name))
                self.collect('.. |%s| %simage:: %s%s\n' % (name, spacer, relpath, src))

                D = dict(imgattrs)
                del D['src']
                recognizedByDocutils = ['alt', 'height', 'width', 'scale', 'align', 'target']
                tokeep = ['alt', 'height', 'width', 'scale', 'target']
                tokeep = ['alt', 'scale', 'target']
                for k in tokeep:
                    if D.has_key(k):
                        if not '%' in D[k]:
                            self.collect('   :%s: %s\n' % (k, D[k]))
                            del D[k]
                for k in sorted(D.keys()):
                    self.collect('.. :%s: %s\n' % (k, D[k]), 'verbatim')
                self.collect('\n')

    def datahandler_html(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_head(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_head
        if self.taginfo:
            if attrs:
                self.sbuf.write('.. <%s>   %r\n\n' % (tag, attrs))

    def stop_head(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.rstrip(CRLF)
        self.collect(s, 'verbatim')
        s = self.collected_metas_tostring()
        if s:
            self.collect('\n\n%s' % s,  'verbatim')
        self.collect('\n\n', 'verbatim')

    def datahandler_head(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_body(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_body
        if self.taginfo:
            if attrs:
                self.collect('.. <%s>   %r\n\n' % (tag, attrs), 'verbatim')
        if 1 and 'include content directory':
            s = (
                '\n'
                '.. sectnum::\n'
                '.. contents::\n'
                '   :backlinks: top\n'
                '\n'
                )
            self.collect(s, 'verbatim')

    def stop_body(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        self.collect(u'%s\n\n' % s, verbatim=True)

    def datahandler_body(self, data, verbatim=None, src=None):
        if 0 and 'page' in data:
            print repr(data)
        self.datahandler_paragraph(data, verbatim)





    def start_div(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_div
        if self.taginfo:
            if attrs:
                self.sbuf.write('.. <%s>   %r\n\n' % (tag, attrs))

    def stop_div(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        self.collect(u'%s\n\n' % s, verbatim=True)

    def datahandler_div(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)






    def start_title(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_title

    def stop_title(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        self.collect(u'%s\n%s\n%s\n\n' % ('='*len(s), s, '='*len(s)),  verbatim=True)

    def datahandler_title(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)






    def start_sectionheader(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_sectionheader

    def stop_sectionheader(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        s = ' '.join([line for line in s.splitlines() if line])
        if s:
            if 'hack - should be resolved':
                self.sbuf.write('\n')

            level = '123456789'.find(tag[1]) + 1
            while (self.sectionlevel+1) < level:
                self.sectionlevel += 1
                g = '((generated))'
                underliner = SECTION_UNDERLINERS[self.sectionlevel-1]
                self.sbuf.write('%s\n%s\n\n' % (g,underliner * len(g)))
            self.sectionlevel = level
            underliner = SECTION_UNDERLINERS[self.sectionlevel-1]
            result = u'%s\n%s\n\n' % (s, underliner*len(s))
            self.sbuf.write(result)

    def datahandler_sectionheader(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_paragraph(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_paragraph

    def stop_paragraph(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        if s:
            if self.fontstack:
                if self.taginfo:
                    self.collect('.. %r\n\n' % self.fontstack)
            if not self.verbatim[-1] and s[0:2] in ['- ', '+ ', '* ', '# ']:
                s = '\\' + s
            if 'tryTextWrapper':
                s = NL.join(TextWrapper(initial_indent='', subsequent_indent='').wrap(s))

            self.collect(u'%s\n\n' % s, verbatim=True, src='paragraph')

    def normdata_paragraph(self, data, src=None):
        """ Normalize incoming data for use in paragraphs.

        Some characters are being escape and multiple whitespace
        characters are replaced by a single blank.

        """
        data = data.replace('\t', ' ')
        data = data.replace('_', '\\_')
        data = data.replace('*', '\\*')
        data = data.replace('|', '\\|')
        data = data.replace('`', '\\`')
        data = data.replace('\r\n', ' ')
        data = data.replace('\n', ' ')
        data = data.replace('\r', ' ')
        lines = data.split()
        if ((self.last_src == 'entityref' or
             self.last_src == 'charref') and data.startswith(' ')):
            lines.insert(0, '')
        if data.endswith(' '):
            lines.append('')
        data = u' '.join(lines)
        return data

    def datahandler_paragraph(self, data, verbatim=None, src=None):
        if not verbatim:
            data = self.normdata_paragraph(data, src)
        if data:
            if self.sbuf.tell() and not self.sbuf.getvalue()[-1] in WHITESPACECHARS:
                pass
                # self.sbuf.write(u' ')
            self.sbuf.write(data)





    def start_li(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_li

    def stop_li(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        listsymbol = self.listsymbolstack[-1]
        indentstr = ' ' * (len(listsymbol)+1)
        s = s.strip()
        s = ['%s%s' % (indentstr, line) for line in s.splitlines()]
        s = NL.join(s)
        s = listsymbol + s[len(listsymbol):]
        if s:
            self.collect(u'%s\n\n' % s, verbatim=True)


    def datahandler_li(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_ul(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_ul
        self.listsymbolstack.append('-')

    def stop_ul(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        self.listsymbolstack.pop()
        s = s.strip(CRLF)
        if s:
            self.collect(u'%s\n\n' % s, verbatim=True)

    def datahandler_ul(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_ol(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_ol
        self.listsymbolstack.append('#.')

    def stop_ol(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        self.listsymbolstack.pop()
        s = s.strip(CRLF)
        if s:
            self.collect(u'%s\n\n' % s, verbatim=True)

    def datahandler_ol(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)




    def start_dl(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_dl
        self.dlstack.append([])

    def stop_dl(self, tag, attrs=[]):
        dlstack = self.dlstack.pop()
        previous = ''
        dtpresent = False
        for k,v in dlstack:
            if k == 'dt':
                dtpresent = True
                break
        if dlstack:
            s = self.sbuf.getvalue().strip(CRLF)
            self.sbuf.truncate(len(s))
            self.sbuf.write(NL)
            for dtdd, s in dlstack:
                s = s.strip()
                if not dtpresent:
                    self.sbuf.write('\n%s\n\n' % s)
                elif dtdd == 'dt':
                    if previous in ['dt', 'dd']:
                        self.sbuf.write('\n')
                    self.sbuf.write('%s\n' % s)
                    previous = dtdd
                elif dtdd == 'dd':
                    if previous == 'dd':
                        self.sbuf.write('\n')
                    s = NL.join(['   %s' % line for line in s.splitlines()])
                    self.sbuf.write('%s\n' % s)
                    previous = dtdd
            self.sbuf.write(NL)
        s = self.sbuf.getvalue()
        self.pop()
        if s:
            self.collect(s, verbatim=True)

    def datahandler_dl(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)




    def start_dt(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_dt

    def stop_dt(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        self.dlstack[-1].append((tag, s))

    def datahandler_dt(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)




    def start_dd(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_dd

    def stop_dd(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        self.dlstack[-1].append((tag, s))

    def datahandler_dd(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)




    def start_a(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_a

    def stop_a(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        if self.verbatim[-1]:
            self.collect(s, 'verbatim', src='a')
        else:
            href = dict(attrs).get('href', None)
            used = False
            if s:
                if href:
                    spacer = ' '
                    if self.sbuf.tell() and self.sbuf.getvalue()[-1] in WHITESPACECHARS:
                        spacer = ''
                    self.collect('%s`%s <%s>`_ ' % (spacer, s, href), 'verbatim', src='a')
                    used = True
                else:
                    self.collect('%s' % s, 'verbatim', src='a')
            if not href:
                self.parent.unused_atags_without_href_log.append((tag, attrs, (self.parent.lineno, self.parent.offset)))
            elif not used:
                self.parent.unused_atags_with_href_log.append((tag, attrs, (self.parent.lineno, self.parent.offset)))

    def datahandler_a(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_table(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_table
        self.tablestack.append(TableDescriptor())

    def stop_table_AndWrite_field_list_table(self, tag, attrs=[]):
        TD = self.tablestack.pop()
        headerrows = TD.headerrows
        if headerrows >= (TD.maxrow + 1):
            headerrows =  TD.maxrow

        s = self.sbuf.getvalue()
        self.pop()

        totalwidth = 0
        if len(TD.colwidths):
            for v in TD.colwidths:
                if v:
                    try:
                        totalwidth += int(v)
                    except ValueError:
                        pass
        if s:
            if self.tablesas == 'flt':
                self.collect('.. field-list-table::\n', 'verbatim')
            else:
                self.collect('.. t3-field-list-table::\n', 'verbatim')
            self.collect(' :header-rows: %s\n' % headerrows, 'verbatim')
            if 0 and totalwidth and not totalwidth == 100:
                self.collect(' :total-width: %s\n' % totalwidth, 'verbatim')
            self.collect('\n', 'verbatim')
            self.collect('%s' % s, 'verbatim')

    def stop_table_AndWrite_neutral(self, tag, attrs=[]):
        TD = self.tablestack.pop()
        headerrows = TD.headerrows
        if headerrows >= (TD.maxrow + 1):
            headerrows =  TD.maxrow

        s = self.sbuf.getvalue()
        self.pop()

        totalwidth = 0
        if len(TD.colwidths):
            for v in TD.colwidths:
                if v:
                    try:
                        totalwidth += int(v)
                    except ValueError:
                        pass
        if s:
            self.collect('.. ### BEGIN~OF~TABLE ###\n\n', 'verbatim')
            self.collect('%s' % s, 'verbatim')
            self.collect('.. ###### END~OF~TABLE ######\n\n', 'verbatim')

    def datahandler_table(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)



    def start_thead(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_thead

    def stop_thead(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        s = self.sbuf.getvalue()
        self.pop()
        # s = s.strip(CRLF)
        if s:
            self.collect('%s' % s, 'verbatim')

    def datahandler_thead(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)




    def start_tbody(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_tbody

    def stop_tbody(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        s = self.sbuf.getvalue()
        self.pop()
        # s = s.strip(CRLF)
        if s:
            self.collect('%s' % s, 'verbatim')

    def datahandler_tbody(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)




    def start_tr(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        row = TD.nextRow()
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_tr

    def stop_tr_AndWrite_field_list_table(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip(CRLF)
        if s:
            s = NL.join(['   %s' % line for line in s.splitlines()])
            self.collect(' -%s\n\n\n\n' % s[2:], 'verbatim')

    def stop_tr_AndWrite_definition_list_container(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip(CRLF)
        if s:
            self.collect('.. container:: table-row\n\n', 'verbatim')
            s = NL.join(['   %s' % line for line in s.splitlines()])
            self.collect('%s\n\n\n' % s, 'verbatim')

    def datahandler_tr(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)



    def start_th(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_th
        TD = self.tablestack[-1]
        col = TD.nextCol()
        if TD.col == 0 and TD.row == TD.headerrows:
            TD.headerrows += 1

    def stop_th_AndWrite_field_list_table(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        colname = TD.getColName(s)
        if 0 and (len(TD.colwidths) > TD.col) and TD.colwidths[TD.col]:
            colwidth = ',%s' % (TD.colwidths[TD.col],)
        else:
            colwidth = ''
        self.collect(':%s%s:\n' % (colname, colwidth), 'verbatim')
        s = NL.join(['      %s' % line for line in s.splitlines()])
        self.collect('%s\n\n' % s, 'verbatim')

    def stop_th_AndWrite_definition_list(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        colname = TD.getColName(s)
        if 0 and (len(TD.colwidths) > TD.col) and TD.colwidths[TD.col]:
            colwidth = ',%s' % (TD.colwidths[TD.col],)
        else:
            colwidth = ''
        self.collect('%s\n' % (colname, ), 'verbatim')
        s = NL.join(['      %s' % line for line in s.splitlines()])
        self.collect('%s\n\n' % s, 'verbatim')

    def datahandler_th(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim=1)



    def start_td(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_table

    def stop_td_AndWrite_field_list_table(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        col = TD.nextCol()
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        s = NL.join(['      %s' % line for line in s.splitlines()])
        colname = TD.getColName()
        self.collect(':%s:\n' % colname, 'verbatim')
        self.collect('%s\n\n' % s, 'verbatim')

    def stop_td_AndWrite_definition_list(self, tag, attrs=[]):
        TD = self.tablestack[-1]
        col = TD.nextCol()
        s = self.sbuf.getvalue()
        self.pop()
        s = s.strip()
        s = NL.join(['      %s' % line for line in s.splitlines()])
        colname = TD.getColName()
        self.collect('%s\n' % colname, 'verbatim')
        self.collect('%s\n\n' % s, 'verbatim')

    def datahandler_td(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim=1)

    # write tables as definition lists
    stop_table = stop_table_AndWrite_neutral
    stop_tr = stop_tr_AndWrite_definition_list_container
    stop_th = stop_th_AndWrite_definition_list
    stop_td = stop_td_AndWrite_definition_list

    ## # write tables as t3-field-list-table directives
    ## stop_table = stop_table_AndWrite_field_list_table
    ## stop_tr = stop_tr_AndWrite_field_list_table
    ## stop_th = stop_th_AndWrite_field_list_table
    ## stop_td = stop_td_AndWrite_field_list_table

    def start_inlinemarkup(self, tag, attrs=[]):
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_inlinemarkup
        if tag == 'font':
            self.fontstack.append(attrs)



    # reStructuredText Interpreted Text Roles
    # http://docutils.sourceforge.net/docs/ref/rst/roles.html
    # http://srv123.typo3.org/~mbless/DOCROOT_HTDOCS/World/Docutils/html/docutils-docs/peps/ref/rst/roles.html

    # :emphasis:
    # reStructuredText Interpreted Text Roles
    # http://docutils.sourceforge.net/docs/ref/rst/roles.html
    # http://srv123.typo3.org/~mbless/DOCROOT_HTDOCS/World/Docutils/html/docutils-docs/peps/ref/rst/roles.html

    # docutils default text roles

    # ====================== ========================= ================= =================
    # from html              role                      inline markup     to html
    # ====================== ========================= ================= =================
    # <i>text</i>            :emphasis:`text`          *text*            <i>text</i>
    #                        :literal:`text`

    #                        :code:`text`
    # <tt>text</tt>          .. literal                ``text``          <tt>text</tt>

    #                        :math:`text`

    #                        :pep-reference:`text`
    #                        :pep:`text`

    #                        :rfc-reference:`text`
    #                        :rfc:`text`

    # <strong>text</strong>  :strong:`text`            **text**          <b>text</b>
    # <b>text</b>            :strong:`text`            **text**          <b>text</b>

    # <sub>text</sub>        :subscript:`text`                           <sub>text</sub>
    # <sub>text</sub>        :sub:`text`                                 <sub>text</sub>

    # <sup>text</sup>        :superscript:`text`                         <sup>text</sup>
    # <sup>text</sup>        :sup:`text`                                 <sup>text</sup>

    # <cite>text</cite>      :title-reference:`text`                     <cite>text</cite>
    # <cite>text</cite>      :title:`text`                               <cite>text</cite>
    # <cite>text</cite>      :t:`text`                                   <cite>text</cite>

    # ====================== ========================= ================= =================


    def stop_inlinemarkup(self, tag, attrs=[]):
        s = self.sbuf.getvalue()
        self.pop()
        spacer = ''
        if self.sbuf.tell() and not self.sbuf.getvalue()[-1] in WHITESPACECHARS:
            spacer = ' '
        if tag == 'b':
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', 'b')
                else:
                    s = s.strip()
                    if s:
                        self.collect(u' **%s** ' % s, 'verbatim')
        elif tag == 'i':
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', 'i')
                else:
                    s = s.strip()
                    if s:
                        self.collect(u' *%s* ' % s, 'verbatim')
        elif tag in ['u']:
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', 'b')
                else:
                    if MAIN.options['revealUnderlineTags']:
                        s = s.strip()
                        self.collect(u'%s[!%s] %s [/%s] ' % (spacer, tag, s, tag), 'verbatim')
                    else:
                        s = s.strip()
                        if s:
                            self.collect(u'%s:underline:`%s` ' % (spacer, s), 'verbatim')
                            self.is_used_textrole_underline = True

        elif tag in ['tt']:
            if tag:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    s = s.strip()
                    if s:
                        self.collect(u' ``%s`` ' % s, 'verbatim')
        elif tag in ['sup']:
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    s = s.strip()
                    if s:
                        self.collect(u'%s:sup:`%s` ' % (spacer, s), 'verbatim')
        elif tag in ['code']:
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    s = s.strip()
                    if s:
                        self.collect(u'%s:code:`%s` ' % (spacer, s), 'verbatim')
        elif tag in ['sub']:
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    s = s.strip()
                    if s:
                        self.collect(u'%s:sub:`%s` ' % (spacer, s), 'verbatim')
        elif tag in ['cite']:
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    s = s.strip()
                    if s:
                        self.collect(u'%s:title:`%s` ' % (spacer, s), 'verbatim')
        elif tag == 'font':
            self.fontstack.pop()
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    if MAIN.options['revealFontTags']:
                        self.collect(u'[!%s] %s [/%s]' % (tag, s, tag), 'verbatim')
                    else:
                        self.collect(u'%s' % s, 'verbatim')
        else:
            if s:
                if self.verbatim[-1]:
                    self.collect(s, 'verbatim', tag)
                else:
                    if MAIN.options['revealOtherInlineTags']:
                        s = s.strip()
                        self.collect(u'%s[!%s] %s [/%s]' % (spacer, tag, s, tag), 'verbatim')
                    else:
                        self.collect(u'%s' % s, 'verbatim')


    def datahandler_inlinemarkup(self, data, verbatim=None, src=None):
        self.datahandler_paragraph(data, verbatim)





    def start_literalblock(self, tag, attrs=[]):
        self.verbatim.append(True)
        self.push()
        self.sbuf = StringIO()
        self.current_datahandler = self.datahandler_literalblock

    def stop_literalblock(self, tag, attrs=[]):
        self.verbatim.pop()
        data = self.sbuf.getvalue()
        self.pop()
        if self.taginfo:
            self.sbuf.write('\n\n.. taginfo():  <%s> %r\n\n' % (tag, attrs))

        if tag in ['pre']:
            firstline = '::\n'
        else:
            if attrs:
                firstline = '.. <%s>  %r\n' % (tag, attrs)
            else:
                firstline = '.. <%s>\n' % (tag,)

        data = data.lstrip(CRLF)
        if 0 and data and data[0] in WHITESPACECHARS:
            data = '\\' + data
        if data or firstline.startswith('..'):
            if not firstline.startswith('..') or self.taginfo:
                self.sbuf.write(firstline)
                self.sbuf.write('\n')
                lines = data.splitlines()
                lines = ['   %s'%line for line in lines]
                data = '\n'.join(lines)
                self.sbuf.write('%s\n\n' % data)

    def datahandler_literalblock(self, data, verbatim=None, src=None):
        self.sbuf.write(data)



    def collect_literal_block(self, firstline, data, indentation=3):
        firstline = firstline.strip(CRLF)
        if not firstline:
            firstline = '..'
        data = data.strip(CRLF)
        indent = ' ' * indentation
        if data:
            if 0 and (data[0] in WHITESPACECHARS):
                data = '\\%s' % data
            data = '\n'.join(['%s%s' % (indent, line) for line in data.splitlines()])
            self.sbuf.write('%s\n\n%s\n\n' % (firstline, data))

    def collected_metas_tostring(self):
        result = ''
        if self.collected_metas:
            self.push()
            self.sbuf = StringIO()
            self.current_datahandler = self.datahandler_paragraph
            kvlista = []
            kvlistb = []
            for a in self.collected_metas:
                try:
                    k = a[0][1] # name
                    v = a[1][1] # content
                except IndexError:
                    k = None
                    v = None
                if k is None:
                    if 'keep always, because unusual' or self.taginfo:
                        self.collect('.. <meta>  %r\n\n' % a)
                else:
                    k, keep = META_MAPPING.get(k.lower(),(k,1))
                    if len(a) > 2:
                        if 'keep always, because unusual' or self.taginfo:
                            self.collect('.. <meta>  %r\n\n' % a)
                    if keep:
                        v = self.OOHF.decodeMetaDateAndTime(v)
                        kvlista.append((k,v))
                    else:
                        kvlistb.append((k,v))
            if kvlista:
                for k,v in kvlista:
                    k = k.strip()
                    k = ' '.join(k.splitlines())
                    k = ' '.join(k.split())
                    v = v.strip()
                    v = '\n'.join(['      %s' % v for v in v.splitlines()])
                    self.collect(':%s:\n%s\n\n' % (k,v), 'verbatim')
            if kvlistb and self.taginfo:
                for k,v in kvlistb:
                    k = k.strip()
                    k = ' '.join(k.splitlines())
                    k = ' '.join(k.split())
                    v = v.strip()
                    v = '\n'.join(['      %s' % v for v in v.splitlines()])
                    self.collect('.. :%s:\n%s\n\n' % (k,v), 'verbatim')
            result = self.sbuf.getvalue()
            self.pop()
        return result


class MyHTMLParser(HTMLParser.HTMLParser):

    def __init__(self, tagwriter=None, taginfo=0, tablesas='dl'):
        """Initialize and reset this instance."""

        HTMLParser.HTMLParser.__init__(self)
        self.tagwriter = tagwriter
        self.taginfo = taginfo
        self.tablesas = tablesas
        self.taglevel = 0
        self.tagstack = []

        self.datacollector = DataCollector(parent=self, taginfo=taginfo, tablesas=tablesas)
        self.do_we_expect_data = [False]
        self.handled_tags_log = {}
        self.unhandled_tags_log = {}
        self.font_log = {}
        self.unexpected_data = []
        self.unused_atags_with_href_log = []
        self.unused_atags_without_href_log = []


    def tagprinter(self, *args, **kwds):
        kwds['end'] = kwds.get('end','')
        kwds['sep'] = kwds.get('sep','')
        file = kwds['file'] = kwds.get('file', self.tagwriter)
        myprint(*args, **kwds)
        if file:
            # to provide a "live" view - hhm, doesn't work!?
            file.flush()

    def close_still_open_pre_tag_if_necassary(self, tag, attrs):
        if 0 and self.datacollector.verbatim[-1]:
            if self.tagstack[-1][0] == 'pre':
                if tag in ['p', 'td', 'th', 'table', 'li', 'div', 'ul', 'dl','body']: # blocktags - to be completed
                    self.taglevel - 1
                    oldtag, oldattrs = self.tagstack.pop()
                    self.datacollector.stop_literalblock(oldtag, oldattrs)
                    self.do_we_expect_data.pop()


    def handle_starttag(self, tag, attrs):
        # self.close_still_open_pre_tag_if_necassary(tag, attrs)
        self.taglevel += 1
        self.tagstack.append((tag,attrs))
        self.datacollector.last_src = None

        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, tag)
            if attrs:
                self.tagprinter('  ', repr(attrs))
            self.tagprinter(NL)

        if 0:
            print tag,

        if tag in ['p']:
            self.datacollector.start_paragraph(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag in ['b', 'i', 'u', 'span', 'strong', 'font', 'tt', 'code', 'sup', 'sub', 'cite']:
            if tag == 'font':
                self.log_font(tag, attrs)
            self.datacollector.start_inlinemarkup(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag in ['pre', 'style', 'script', 'multicol']:
            self.datacollector.start_literalblock(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag == 'li':
            self.datacollector.start_li(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag == 'ul':
            self.datacollector.start_ul(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag == 'ol':
            self.datacollector.start_ol(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag == 'dl':
            self.datacollector.start_dl(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag == 'dt':
            self.datacollector.start_dt(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag == 'dd':
            self.datacollector.start_dd(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag == 'a':
            self.datacollector.start_a(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif len(tag)==2 and tag[0]=='h' and tag[1] in '123456789':
            self.datacollector.start_sectionheader(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag in ['title']:
            self.datacollector.start_title(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag in ['div']:
            self.datacollector.start_div(tag, attrs)
            self.do_we_expect_data.append(True)
            self.log_handled_tags(tag, attrs)

        elif tag in ['table']:
            self.datacollector.start_table(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['thead']:
            self.datacollector.start_thead(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['tbody']:
            self.datacollector.start_tbody(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['td']:
            self.datacollector.start_td(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['tr']:
            self.datacollector.start_tr(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['th']:
            self.datacollector.start_th(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['body']:
            self.datacollector.start_body(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['head']:
            self.datacollector.start_head(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        elif tag in ['html']:
            self.datacollector.start_html(tag, attrs)
            self.do_we_expect_data.append(False)
            self.log_handled_tags(tag, attrs)

        else:
            # log the unhandled tag
            # nevertheless keep data processing like before
            self.log_unhandled_tags(tag, attrs)


    def handle_endtag(self, tag):
        self.datacollector.last_src = None
        # self.close_still_open_pre_tag_if_necassary(tag, [])
        if self.tagwriter:
            if (0):
                self.tagprinter('  ' * self.taglevel, '%s' % self.datacollector.debuginfo('sbufs'), NL)
            self.tagprinter('  ' * self.taglevel, '/%s'%tag, NL)
        self.taglevel -= 1
        tag0, attrs = self.tagstack.pop()
        if not tag0 == tag:
            print
            print 'ERROR at line %s, column %s: unbalanced tags in \'%s\'' % (self.lineno, self.offset, args.infile)
            print '      %s%s  shall be closed but' % (tag,  ' '*(10-len(tag)))
            print '      %s%s  found in stack.'     % (tag0, ' '*(10-len(tag0)))
            print '      %r' % ([t[0] for t in self.tagstack] + [tag0])
            print
            sys.exit(1)
            # raise "error"

        # some html inline tags: b, i, tt, u, strike, s, big, small, sup, sub
        # standard docutils text roles: :emphasis:, :literal:, :code:, :math:, :pep-reference:
        # :rfc-reference:, :string:, :subscript:, :superscript:
        if 0:
            print '/%s' % tag,

        if tag in ['p']:
            self.datacollector.stop_paragraph(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['b', 'i', 'u', 'span', 'strong', 'font', 'tt', 'code', 'sup', 'sub', 'cite']:
            self.datacollector.stop_inlinemarkup(tag, attrs)
            self.do_we_expect_data.pop()

        elif tag in ['pre']:
            if 0 and 'hack! to cope with error in input xml document':
                self.taglevel += 1
                self.tagstack.append((tag0,attrs))
            else:
                self.datacollector.stop_literalblock(tag, attrs)
                self.do_we_expect_data.pop()

        elif tag in ['style', 'script', 'multicol']:
            self.datacollector.stop_literalblock(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'li':
            self.datacollector.stop_li(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'ul':
            self.datacollector.stop_ul(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'ol':
            self.datacollector.stop_ol(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'dl':
            self.datacollector.stop_dl(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'dt':
            self.datacollector.stop_dt(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'dd':
            self.datacollector.stop_dd(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag == 'a':
            self.datacollector.stop_a(tag, attrs)
            self.do_we_expect_data.pop()
        elif len(tag)==2 and tag[0]=='h' and tag[1] in '123456789':
            self.datacollector.stop_sectionheader(tag, attrs)
            self.do_we_expect_data.append(False)
        elif tag in ['title']:
            self.datacollector.stop_title(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['div']:
            self.datacollector.stop_div(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['table']:
            self.datacollector.stop_table(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['thead']:
            self.datacollector.stop_thead(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['tbody']:
            self.datacollector.stop_tbody(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['tr']:
            self.datacollector.stop_tr(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['td']:
            self.datacollector.stop_td(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['th']:
            self.datacollector.stop_th(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['body']:
            self.datacollector.stop_body(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['head']:
            self.datacollector.stop_head(tag, attrs)
            self.do_we_expect_data.pop()
        elif tag in ['html']:
            self.datacollector.stop_html(tag, attrs)
            self.do_we_expect_data.pop()
        else:
            # end of unhandled tag
            pass

        if 0:
            print self.datacollector.debuginfo('sbufs')


    def handle_startendtag(self, tag, attrs):
        self.datacollector.last_src = None
        # self.close_still_open_pre_tag_if_necassary(tag, attrs)
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, tag)
            if attrs:
                self.tagprinter('  ', repr(attrs))
            self.tagprinter(NL)

        if tag in ['br']:
            self.datacollector.collect(NL, src='startendtag')
            self.log_handled_tags(tag, attrs)

        elif tag in ['img']:
            self.datacollector.handle_img(tag, attrs)
            self.log_handled_tags(tag, attrs)

        elif tag in ['col']:
            if self.datacollector.tablestack:
                TD = self.datacollector.tablestack[-1]
                D = dict(attrs)
                width = D.get('width','')
                TD.colwidthsraw.append(width)
                width = ''.join([c for c in width if c in '0123456789'])
                TD.colwidths.append(width)
                self.log_handled_tags(tag, attrs)
            else:
                self.log_unhandled_tags(tag, attrs)

        elif tag in ['meta']:
            self.datacollector.handle_meta(tag, attrs)
            self.log_handled_tags(tag, attrs)

        else:
            self.log_unhandled_tags(tag, attrs)


    def handle_data(self, data):
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, '%r' % data[:50], NL)

        if 1 or self.do_we_expect_data[-1]:
            self.datacollector.collect(data, src='data')

        if not self.do_we_expect_data[-1]:
            s = data.strip()
            if s:
                tags = []
                i = 0
                for k,v in self.tagstack:
                    if self.do_we_expect_data[i]:
                        tags.append('%s-1' % k)
                    else:
                        tags.append('%s-0' % k)
                    i += 1

                tags = '>'.join(tags)
                self.unexpected_data.append((s, (self.lineno, self.offset), tags))


    def handle_charref(self, name):
        try:
            if name[0] in ['x','X']:
                c = int(s[1:], 16)
            else:
                c = int(name)
            u = unichr(c)
        except ValueError:
            u = '&#' + name + ';'
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, 'charref: %s  %r' % (name, u), NL)
        self.datacollector.collect(u, src='charref')

    def handle_entityref(self, name):
        u = entitydefs[name]
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, 'entityref: %s  %r' % (name, u), NL)
        self.datacollector.collect(u, src='entityref')

    def handle_comment(self, data):
        self.datacollector.last_src = None
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, data, NL)
        if self.taginfo:
            firstline = '.. <!-- comment -->'
            self.datacollector.collect_literal_block(firstline, data)

    def handle_decl(self, decl):
        self.datacollector.last_src = None
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, decl, NL)

    def handle_pi(self, data):
        self.datacollector.last_src = None
        if self.tagwriter:
            self.tagprinter('  ' * self.taglevel, data, NL)

    def unknown_decl(self, data):
        self.datacollector.last_src = None
        self.error("unknown declaration: %r" % (data,))

    def log_unhandled_tags(self, tag, attrs=[]):
        stats = self.unhandled_tags_log.get(tag, None)
        if stats is None:
            stats = self.unhandled_tags_log[tag] = [0, []]
        stats[0] += 1
        stats[1].append(self.lineno)

    def log_handled_tags(self, tag, attrs=[]):
        stats = self.handled_tags_log.get(tag, None)
        if stats is None:
            stats = self.handled_tags_log[tag] = [0, []]
        stats[0] += 1
        stats[1].append(self.lineno)

    def log_font(self, tag, attrs=[]):
        stats = None
        for attr in attrs:
            stats = self.font_log.get(attr, None)
        if stats is None:
            stats = self.font_log[''] = [0, []]
        stats[0] += 1
        if 0and 'lets not collect linenumbers here':
            stats[1].append(self.lineno)

    def tags_log_as_string(self, D={}):
        sbuf = StringIO()
        keys = D.keys()
        keys = sorted(keys)
        maxlen = 4
        for k in keys:
            maxlen = max(maxlen, len(k))
        initial_indent = ''
        subsequent_indent = ' ' * (maxlen+10)

        sbuf.write('%s'  '  =====   ===============\n' % ('='* maxlen   ,))
        sbuf.write('name%s  n       line numbers' '\n' % (' '*(maxlen-4),))
        sbuf.write('%s'  '  =====   ===============\n' % ('='* maxlen   ,))

        for k in keys:
            filler = ' ' * (maxlen - len(k))
            linenums = []
            for i in D[k][1]:
                linenums.append('%s' % i)
            linenums = ', '.join(linenums)
            linenums = u'%s%s  %5d   %s' % (k, filler, D[k][0], linenums )
            if 'do wrapping' and 0:
                linenums = TextWrapper(initial_indent=initial_indent, subsequent_indent=subsequent_indent).wrap(linenums)
            else:
                linenums = linenums.splitlines()
            for i, s in enumerate(linenums):
                sbuf.write(s)
                sbuf.write(NL)
            sbuf.write(NL)
        sbuf.write('%s'  '  =====   ===============\n' % ('='* maxlen   ,))
        sbuf.write(NL)
        return sbuf.getvalue()

def searchFileEncoding(f1name):
    """Check some lines to see if we have an encoding information."""
    f1 = file(f1name)
    cnt = 0
    result = None
    xmlDeclarationFound = False
    maxLinesToCheck = 100
    for line in f1:
        if cnt == 0 and line.startswith('\xef\xbb\xbf'):
            result = 'utf-8'
            break
        line = line.strip().lower()
        if line:
            if line.startswith('<?xml') :
                r = re.search('''encoding\s*=\s*['"](.*)['"]''', line)
                if r:
                    result = r.group(1).strip()
                    if result:
                        xmlDeclarationFound = True
                        break
            elif 'charset' in line:
                # <META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=windows-1252">
                # text/html; charset=utf-8" />
                r = re.search('''charset=(.*)['"]\s*/?>''', line)
                if r:
                    result = r.group(1).strip()
                    if result:
                        break
            cnt += 1
            if maxLinesToCheck and cnt > maxLinesToCheck:
                break
    f1.close()
    if result:
        try:
            ' '.encode(result)
        except LookupError:
            result = None
    return result, xmlDeclarationFound



def main(f1name, f2name, f3name=None, f4name=None, appendlog=0, taginfo=0, tablesas='dl'):

    f1 = None
    f2 = None
    f3 = None
    f4 = None
    f1encoding = 'utf-8'
    xmlDeclarationFound = None

    if f1name == '-':
        f1 = sys.stdin
    elif False and f1 is None and f1name.startswith('http://') or f1name.startswith('https://'):
        import urllib
        f1 = urllib.urlopen(f1name)
    elif f1 is None and f1name.startswith('http://') or f1name.startswith('https://'):
        import urllib
        url = f1name
        f1name = 'temp-urlretrieved.html'
        urllib.urlretrieve(url, f1name)
        urllib.urlcleanup()

    if f1 is None:
        f1encoding, xmlDeclarationFound = searchFileEncoding(f1name)
        f1 = codecs.open(f1name, 'r', f1encoding)

    if f2name == '-':
        f2 = sys.stdout
    else:
        f2 = codecs.open(f2name, 'w', 'utf-8-sig')


    # treefile
    f3 = None
    if f3name:
        # buffersize 0 in the hope to get unbuffered output
        f3 = codecs.open(f3name, 'w', 'utf-8-sig', 'strict', 0)

    # logfile
    f4 = None
    if f4name:
        # buffersize 0 in the hope to get unbuffered output
        f4 = codecs.open(f4name, 'w', 'utf-8-sig')

    P = MyHTMLParser(tagwriter=f3, taginfo=taginfo, tablesas=tablesas)

    try:

        maxlines = None
        for cnt, line in enumerate(f1):
            P.feed(line)
            if maxlines and (cnt+1) >= maxlines:
                break

        if 1:
            blocktitle = 'Attributes of <font>::'
            if not P.font_log:
                P.font_log['None'] = 'None'
            s = StringIO()
            pprint(P.font_log, s, indent=1, width=69)
            s = s.getvalue()
            if appendlog:
                P.datacollector.collect_literal_block(blocktitle, s)
            if f4:
                s = '\n'.join(['   %s' % line for line in s.splitlines()])
                f4.write('%s\n\n%s\n\n' % (blocktitle, s))

        if 1:
            blocktitle = 'List of handled tags:'
            s = P.tags_log_as_string(P.handled_tags_log)
            s = NL.join([line for line in s.splitlines() if line])
            if appendlog:
                P.datacollector.collect_literal_block(blocktitle, s)
            if f4:
                f4.write('%s\n\n%s\n\n' % (blocktitle, s))

        if 1:
            blocktitle = 'List of unhandled tags::'
            s = P.tags_log_as_string(P.unhandled_tags_log)
            s = NL.join([line for line in s.splitlines() if line])
            if appendlog:
                P.datacollector.collect_literal_block(blocktitle, s)
            if f4:
                f4.write('%s\n\n%s\n\n' % (blocktitle, s))

        if 1:
            blocktitle = ('"Unexpected data". This is data we got '
                          'although we are not within an '
                          'appropriate tag::')
            if not P.unexpected_data:
                P.unexpected_data.append('None')
            s = StringIO()
            pprint(P.unexpected_data, s, indent=1, width=69)
            s = s.getvalue()
            if appendlog:
                P.datacollector.collect_literal_block(blocktitle, s)
            if f4:
                s = '\n'.join(['   %s' % line for line in s.splitlines()])
                f4.write('%s\n\n%s\n\n' % (blocktitle, s))


        if 1:
            blocktitle = "Unused a-tags that didn't have 'href'::"
            if not P.unused_atags_without_href_log:
                P.unused_atags_without_href_log.append('None')
            s = StringIO()
            pprint(P.unused_atags_without_href_log, s, indent=1, width=69)
            s = s.getvalue()
            if appendlog:
                P.datacollector.collect_literal_block(blocktitle, s)
            if f4:
                s = '\n'.join(['   %s' % line for line in s.splitlines()])
                f4.write('%s\n\n%s\n\n' % (blocktitle, s))

        if 1:
            blocktitle = "Unused a-tags that did have a 'href' - but no content::"
            if not P.unused_atags_with_href_log:
                P.unused_atags_with_href_log.append('None')
            s = StringIO()
            pprint(P.unused_atags_with_href_log, s, indent=1, width=69)
            s = s.getvalue()
            if appendlog:
                P.datacollector.collect_literal_block(blocktitle, s)
            if f4:
                s = '\n'.join(['   %s' % line for line in s.splitlines()])
                f4.write('%s\n\n%s\n\n' % (blocktitle, s))

        if 0:
            if appendlog:
                msg = ('\n**Use the -a0 or --append-log 0 option at the '
                       'command line to turn these statistics at the end of '
                       'this document off.**\n')
                P.datacollector.collect(msg, 'verbatim')

        result = P.datacollector.stop_document('initial')
        if 1:
            f2.write(SNIPPETS.for_your_information)
        if 0:
            f2.write(SNIPPETS.define_some_textroles)
        else:
            if P.datacollector.is_used_textrole_underline:
                f2.write('.. role:: underline\n\n')

        f2.write(result)

    finally:
        P.close()
        if f2 != sys.stdout:
            f2.close()
        if f1 != sys.stdin:
            f1.close()
        if f3:
            f3.close()
        if f4:
            f4.close()


def get_argparse_args():
    """Get commandline args using module 'argparse'. Python >= 2.7 required."""

    class License(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print __copyright__
            parser.exit()

    class History(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print __history__
            parser.exit()

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], add_help=False)
    parser.add_argument('--help', '-h', action='help', default=argparse.SUPPRESS, help='show this help message and exit')
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('--license', help='show license', nargs=0, action=License)
    parser.add_argument('--history', help='show history', nargs=0, action=History)
    parser.add_argument('--logfile', help='filename to receive parsing statistics', dest='logfile', default=None)
    parser.add_argument('--treefile', help='filename to receive a treelike structure of the input file as seen by the parser', dest='treefile', default=None)
    parser.add_argument('-a', '--append-log', help='append logfile data at then end of outfile. FLAG: 0|1. Default: 0.', dest='appendlog', default=0, type=int, choices=[0,1], metavar='FLAG')
    parser.add_argument('--taginfo', help='include a description of html tags like head, body, style, script etc. as comment into the reST file. FLAG: 0|1. Default: 0.', dest='taginfo', default=0, type=int, choices=[0,1], metavar='FLAG')
    parser.add_argument('--tables-as', help="write tables as 'definition lists' (dl) or as 't3-field-list-table' (flt). Default: dl", dest='tablesas', default='dl', choices=['dl', 'flt', 't3flt'], metavar='dl|flt|t3flt')
    # parser.add_argument('-v', help='verbose - talk to stdout', dest='talk', action='store_true')
    parser.add_argument('infile')
    parser.add_argument('outfile')
    return parser.parse_args()


class Namespace(object):
    """Simple object for storing attributes."""

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])


if __name__=="__main__":

    argparse_available = False
    try:
        import argparse
        argparse_available = True
    except ImportError:
        pass
    if not argparse_available:
        try:
            import local_argparse as argparse
            argparse_available = True
        except ImportError:
            pass
    if argparse_available:
        args = get_argparse_args()
    else:
        args = Namespace()

        # you may hardcode parameters here:
        if 'hardcode parameters here':
            args.infile = ''
            args.outfile = ''
            args.treefile = ''
            args.logfile = ''
            args.appendlog = 0
            args.taginfo = 0
            args.tablesas = 'dl' or 'flt'

        if not args.infile:
            msg = ("\nNote:\n"
                   "   '%(prog)s'\n"
                   "   needs module 'argparse' (Python >= 2.7) to handle commandline\n"
                   "   parameters. It seems that 'argparse' is not available. Provide\n"
                   "   module 'argparse' or hardcode parameters in the code instead.\n" % {'prog': sys.argv[0]} )
            print msg
            sys.exit(2)

    main(args.infile, args.outfile, args.treefile, args.logfile, args.appendlog, args.taginfo, args.tablesas)
