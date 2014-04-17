#! /usr/bin/python
# coding: ascii

# ==================================================
# The following __doc__ string is displayed on --info
# --------------------------------------------------

"""\
t3pdb_sxw2html - T3PythonDocBuilder: Convert from .sxw to .html

This module will convert an OpenOffice document from *.sxw
to *.html. It is intended to be run on a Linux server where
OpenOffice headless is running. You have to provide two
parameters: The complete path to an existing OpenOffice
document and the path to a temporary directory.

Expected parameters:
  infile    full path to OpenOffice source file of type *.sxw
  tempdir   path to a temporary directory.

Example:
  python t3pdb_sxw2html.py  ../src/manual.sxw  ./tempdir/

Example
  t3pdb_sxw2html  ../src/manual.sxw  ./tempdir/

"""

import os
import sys
try:
    import PIL
    from PIL import Image
    PIL_is_available = True
except ImportError:
    PIL_is_available = False


# testing
if 0 and 'pywin' in sys.modules:
    k = 'write_sphinx_structure'
    if sys.modules.get(k, None):
        del sys.modules[k]
    sys.argv = [sys.argv[0]] + ['temp\\manual.sxw', 'temp']

import subprocess
import zipfile
import shutil
import codecs

import copyclean
import ooxhtml2rst
import normalize_empty_lines
import write_sphinx_structure
import prepend_sections_with_labels
## import remove_first_t3fieldlisttable_row
import tweak_dllisttables

ospe = os.path.exists
ospj = os.path.join

NL = '\n'

__version__ = '0.0.1'

# leave your name and notes here:
__history__ = """\

2012-08-26  Martin Bless <martin@mbless.de>
            Starting this rewrite.
2012-08-29  Martin Bless <martin@mbless.de>
   Add option '-O', '--outfile-name'
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

def platformIsLinux():
    return 'linux' in sys.platform

def platformIsWindows():
    return 'win32' in sys.platform

def platformIsMac():
    return 'darwin' in sys.platform

OOHEADLESS_IS_AVAILABLE = False
if platformIsLinux():
    try:
        import oodocconverter_linux
        converter = oodocconverter_linux.DocumentConverter()
        OOHEADLESS_IS_AVAILABLE = True
    except:
        OOHEADLESS_IS_AVAILABLE = False
elif platformIsWindows():
    import oodocconverter_win
    OOHEADLESS_IS_AVAILABLE = True
elif platformIsMac():
    import oodocconverter_mac
else:
    pass

def convertsxw2html(srcfile, destfile):
    if platformIsLinux():
        if OOHEADLESS_IS_AVAILABLE:
            done = False
            try:
                converter.convert(srcfile, destfile)
                retCode, msg = 0, 'Ok'
            except dc.DocumentConversionException, exception:
                retCode, msg = 2, "ERROR1! " + str(exception)
            except dc.ErrorCodeIOException, exception:
                retCode, msg = 2, "ERROR2! " % str(exception)
            except Exception, msg:
                retCode, msg = 2, "ERROR9! " + str(msg)

        else:
            retCode, msg = (2,
                            "'OpenOffice headless for Linux' is not "
                            "available. Cannot convert '%s' to '%s'" %
                            (srcfile, destfile))
        return retCode, msg

    elif platformIsWindows():
        retCode, msg = oodocconverter_win.main(srcfile, destfile)

    elif platformIsMac():
        retCode, msg = oodocconverter_mac.main(srcfile, destfile)

    else:
        retCode, msg = 1, "There's no converter for platform '%s'" % sys.platform

    return retCode, msg


class Namespace(object):
    """Simple object for storing attributes."""

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])


class Main:

    def __init__(self, args):
        self.args = args
        self.tempdirname = 't3pdb'

        # where do we have our resources?
        self.resdir = 'resources'

        self.safetempdir = ospj(self.args.tempdir, self.tempdirname)
        if self.args.logdir:
            self.logdir = self.args.logdir
        else:
            self.logdir = ospj(self.safetempdir, 'logs')

        self.f1path = self.args.infile
        self.f1name = os.path.basename(self.f1path)
        self.f1stem, self.f1ext = os.path.splitext(self.f1name)

        if self.args.outfilename:
            self.f2name = os.path.basename(self.args.outfilename)
            self.f2stem, self.f2ext = os.path.splitext(self.f2name)
        else:
            self.f2ext = '.html'
            self.f2stem = 'manual'
            self.f2name = self.f2stem + self.f2ext

        self.f2path = ospj(self.safetempdir, self.f2name)
        self.f2path_cleaned = ospj(self.safetempdir, self.f2stem + '-cleaned' + self.f2ext)
        self.f2path_from_tidy = ospj(self.safetempdir, self.f2stem + '-from-tidy' + self.f2ext)
        self.f2path_rst = ospj(self.safetempdir, self.f2stem + '.rst')
        self.f2path_rst_temp = ospj(self.safetempdir, self.f2stem + '-temp.rst')
        self.safetempdir_sliced = ospj(self.safetempdir, '_sliced')
        self.f2path_documentation = ospj(self.safetempdir, 'Documentation')

        # logfiles
        self.f2path_tidy_error_log = ospj(self.logdir, self.f2name + '.tidy-error-log.txt')
        self.f2path_rst_treefile = ospj(self.logdir, self.f2name + '.restparser-tree.txt')
        self.f2path_rst_logfile = ospj(self.logdir, self.f2name + '.restparser-log.txt')

        # more settings
        self.usr_bin_python = '/usr/bin/python'
        self.usr_bin_python = 'python'
        self.t3docutils_stylesheet_path = 'http://docs.typo3.org/css/typo3_docutils_styles.css'
        self.t3rst2html_script = 't3rst2html.py'
        self.t3docutils_template_path = 'resources/t3docutils_template.txt'

        self.rstfilepaths = []



    def work(self):
        retCode = 0
        msg = ''
        if self.args.outfilename:
            if self.f2name != self.args.outfilename:
                return 1, "Specify outfilename without path. Found: '%s'" % self.args.outfilename
            if self.f2ext != '.html':
                return 1, "Specify 'outfilename' with '.html'. Found: '%s'" % self.args.outfilename
        try:
            f1 = file(self.args.infile)
        except:
            retCode, msg = 1, "Cannot read file '%s'" % self.args.infile
            return retCode, msg


        if not os.path.isdir(self.args.tempdir):
            retCode, msg = (1,
                            "Cannot find tempdir '%s'" % self.args.tempdir)
            return retCode, msg

        if os.path.isdir(self.safetempdir):
            try:
                shutil.rmtree(self.safetempdir)
            except:
                retCode, msg = (1,
                                "Cannot remove safetempdir '%s'" %
                                self.safetempdir)
                return retCode, msg

        if os.path.isdir(self.safetempdir):
            retCode, msg = (1,
                            "Cannot remove safetempdir '%s'" %
                            self.safetempdir)
            return retCode, msg
        else:
            try:
                os.makedirs(self.safetempdir)
            except:
                retCode, msg = (1,
                                "Cannot create safetempdir '%s'" %
                                self.safetempdir)
                return retCode, msg

        if self.logdir == ospj(self.safetempdir, 'logs'):
            os.makedirs(self.logdir)
        else:
            if not os.path.isdir(self.logdir):
                return 1, "Cannot find logdir '%s'" % self.logdir
            try:
                f2path = ospj(self.logdir, 'test.txt')
                f2 = file(f2path, 'w')
                f2.close()
                os.unlink(f2path)
            except IOError:
                return 1, "Cannot write to file in logdir: '%s'" % f2path


        # let's check the manual.sxw is not corrupted in some way
        tested = False
        try:
            iszipfile = zipfile.is_zipfile(self.f1path)
            tested = True
        except:
            pass

        if not tested:
            retCode, msg = (1,
                            "Cannot test '%s' for being a zipfile" %
                            self.f1path)
            return retCode, msg
        elif not iszipfile:
            retCode, msg = (1, "'%s' is not a zipfile" % self.f1path)
            return retCode, msg
        else:
            pass

        error = None
        try:
            zf = zipfile.ZipFile(self.f1path)
            testresult = zf.testzip()
            error = None
        except IOError:
            error = 'IOError'
        except:
            error = 'Unknown Error'
        if error:
            retCode, msg = (1,
                            "'%s' looks like a zipfile but could not "
                            "be tested with zipfiletest" %
                            self.f1path)
            return retCode, msg
        if testresult:
            retCode, msg = (1,
                            "'%s' is a zipfile but not legal in some "
                            "aspects" % self.f1path)

        retCode, msg = convertsxw2html(self.f1path, self.f2path)
        if retCode:
            return retCode, msg

        if 0:
            cmd = 'chmod +r ' + ospj(self.safetempdir, '*')
            subprocess.call(cmd, shell=True)


        if 1 and "convert *.gif to *.gif.png":
            L = []
            dirname = os.path.dirname(self.f2path)
            for fname in os.listdir(dirname):
                if fname.lower().startswith('manual_html_') and fname.lower().endswith('.gif'):
                    L.append(fname)
            if L:
                for fname in L:
                    gifFile = ospj(dirname, fname)
                    im = PIL.Image.open(gifFile)
                    pngFile = gifFile + '.png'
                    im.save(pngFile)
                f1 = file(self.f2path)
                data = f1.read()
                f1.close()
                for fname in L:
                    data = data.replace(fname, fname + '.png')
                f2 = file(self.f2path, "w")
                f2.write(data)
                f2.close()

        if 1:
            try:
                copyclean.main(self.f2path, self.f2path_cleaned)
            except:
                retCode, msg = (1,
                                "Cannot run 'copyclean.main()")
                return retCode, msg

        if 1:
            # manual-cleaned.html -> manual-from-tidy.html
            # # step: Use tidy to convert from HTML-4 to XHTML
            # tidy -asxhtml -utf8 -f $EXTENSIONS/$EXTKEY/nightly/tidy-error-log.txt -o $EXTENSIONS/$EXTKEY/nightly/2-from-tidy.html $EXTENSIONS/$EXTKEY/nightly/1-cleaned.html

            cmd = ' '.join(['tidy', '-asxhtml', '-utf8', '-f', self.f2path_tidy_error_log, '-o', self.f2path_from_tidy, self.f2path_cleaned])
            retCode = subprocess.call(cmd, shell=True)
            if not ospe(self.f2path_from_tidy):
                retCode, msg = (1,
                                "Cannot create '%s'" %
                                self.f2path_from_tidy)



        if 1:
            # parse from *.html to *.rst
            arg = Namespace()
            arg.infile = self.f2path_from_tidy
            arg.outfile = self.f2path_rst
            arg.treefile = None  # no treefile
            arg.treefile = self.f2path_rst_treefile
            arg.logfile = None   # no logfile
            arg.logfile = self.f2path_rst_logfile
            arg.appendlog = 0
            arg.taginfo = 0

            tabletypes = ['t3flt', 'dl', 'flt']
            tabletypes = ['t3flt', 'dl']
            for i,tablesas in enumerate(tabletypes):
                outfile = arg.outfile[:-3] + tablesas + '.rst'
                ooxhtml2rst.main(arg.infile, outfile, arg.treefile,
                                 arg.logfile, arg.appendlog, arg.taginfo, tablesas)
                if not os.path.exists(outfile):
                    return 1, "ooxhtml2rst.main(): could not create ReST file '%s'" % outfile
                if i == 0:
                    self.f2path_rst = outfile
                    arg.treefile = None
                    arg.logfile = None


        self.rstfilepaths = []
        for fname in os.listdir(self.safetempdir):
            if fname.endswith('.rst'):
                fpath = ospj(self.safetempdir, fname)
                if os.path.isfile(fpath):
                    self.rstfilepaths.append(fpath)


        if 1:
            # for each of our newly created *.rst provide a Docutils rendering
            # errorfilename = 'sxw2html-conversion-error.txt'
            # self.t3docutils_stylesheet_path
            # self.usr_bin_python
            # self.t3rst2html_script
            # self.safetempdir

            for f2path_rst in self.rstfilepaths:
                normalize_empty_lines.main(f2path_rst, self.f2path_rst_temp, 2)
                os.remove(f2path_rst)
                os.rename(self.f2path_rst_temp, f2path_rst)


        if 1:
            arg = Namespace()
            arg.pathToTemplate = self.t3docutils_template_path

            for arg.srcfile in self.rstfilepaths:
                arg.basename = os.path.basename(arg.srcfile)
                temp = arg.basename
                temp = temp.replace('.dl.html', '.html')
                temp = temp.replace('.flt.html', '.html')
                temp = temp.replace('.t3flt.html', '.html')
                arg.basename_generic = temp
                arg.destfile = arg.srcfile[:-4] + '.html'
                arg.warningsfile = ospj(self.logdir, arg.basename_generic + '.t3rst2html-warnings.txt')
                cmd = ' '.join([
                    self.usr_bin_python,
                    self.t3rst2html_script,
                    '--source-link',
                    # '--link-stylesheet',
                    # '--stylesheet-path=%s' % stylesheet_path,
                    '--template=%s' % arg.pathToTemplate,
                    '--field-name-limit=0',
                    '--warnings=%s' % arg.warningsfile,
                    arg.srcfile,
                    arg.destfile,
                ])
                arg.stdout_log = ospj(self.logdir, arg.basename_generic + '.t3rst2html-stdout.txt')
                arg.stderr_log = ospj(self.logdir, arg.basename_generic + '.t3rst2html-stderr-log.txt')
                # errors = 'strict', 'replace', 'ignore', 'xmlcharrefreplace', 'backslashreplace'
                f2stdout = codecs.open(arg.stdout_log, 'w', 'utf-8', errors='backslashreplace')
                f2stderr = codecs.open(arg.stderr_log, 'w', 'utf-8', errors='backslashreplace')
                # devnull = file('/dev/null', 'w')
                returncode = subprocess.call(cmd, stdout=f2stdout, stderr=f2stderr, shell=True)
                f2stderr.close()
                f2stdout.close()
                # returncode = subprocess.call(cmd, shell=True)
                # devnull.close()


        # ==================================================
        # make ./Documentation structure
        # --------------------------------------------------

        if 1 and 'select the rst file with the desired table handling':
            for self.f2path_rst in self.rstfilepaths:
                if self.f2path_rst.endswith('.t3flt.rst'):
                    pass
                if self.f2path_rst.endswith('.dl.rst'):
                    break
            else:
                self.f2path_rst = None

        arg = Namespace()
        arg.f2path_rst = self.f2path_rst
        arg.safetempdir_sliced = self.safetempdir_sliced
        arg.f2path_documentation = self.f2path_documentation
        arg.srcdirimages = self.safetempdir
        arg.resdir = self.resdir
        retCode, msg = write_sphinx_structure.main(arg)


        # travel all *.rst files in ./Documentation and
        # insert an intersphinx label before each section
        # only underlined sections are recognized
        prepend_sections_with_labels.main(self.f2path_documentation)


        ## ####
        ## Ah, oh, uh, this was a silly idea. Forget it.
        ##
        ## # travel all *.rst files in ./Documentation and
        ## # try to check whether the first row of a .. t3-field-list-table::
        ## # should be removed. If so do so.
        ## remove_first_t3fieldlisttable_row.main(self.f2path_documentation)


        # travel all *.rst files in ./Documentation and
        # and try to tweak the '.. container:: table-row' of 'definition list tables'
        tweak_dllisttables.main(self.f2path_documentation)



        retCode = 0
        msg = "Ok"
        return retCode, msg


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

    class Info(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print
            print __doc__
            parser.exit()

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], add_help=False)
    parser.add_argument('--help', '-h', action='help', default=argparse.SUPPRESS, help='show this help message and exit')
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('--license', help='show license', nargs=0, action=License)
    parser.add_argument('--history', help='show history', nargs=0, action=History)
    parser.add_argument('--info',    help='show more information about this module', nargs=0, action=Info)
    parser.add_argument('-O', '--outfile-name', help=\
                        "The default outfile is 'manual.html'. Specify "
                        "'aDifferentName.html' to override", dest='outfilename', default=None)
    parser.add_argument('--logdir', help="Existing directory where logs will be written. Defaults to tempdir/t3pdb/logs which will be created.", dest='logdir', default=None)
    parser.add_argument('infile')
    parser.add_argument('tempdir')
    return parser.parse_args()



if __name__=="__main__":

    if 0 and "fake arguments":
        sys.argv = sys.argv[0:1] + ['temp/manual.sxw', 'temp']

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
            args.tempdir = ''

        if not args.infile:
            msg = ("\nNote:\n"
                   "   '%(prog)s'\n"
                   "   needs module 'argparse' (Python >= 2.7) to handle commandline\n"
                   "   parameters. It seems that 'argparse' is not available. Provide\n"
                   "   module 'argparse' or hardcode parameters in the code instead.\n" % {'prog': sys.argv[0]} )
            print msg
            sys.exit(2)

    main = Main(args)
    retCode = 0
    if retCode == 0:
        retCode, msg = main.work()
    if retCode == 0:
        pass

    if retCode:
        print "Error:"
        print "  retCode:", retCode
        print "  message:", msg
    else:
        print "Success:", msg
    print "Please see README.rst"
