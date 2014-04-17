"""\
Copy infile to outfile and thereby do some cleaning.

"-" may be used for stdin or stdout.
"<sdfield>" tags will be removed.

"""


__version__ = '1.0.0'

# leave your name and notes here:
__history__ = """\

2012-04-22  Martin Bless <martin@mbless.de>
            initial realease
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


import sys

def main(f1name, f2name):
    if f1name != '-':
        f1 = file(f1name, 'r')
    else:
        f1 = sys.stdin
    data = f1.read()
    if f1name != '-':
        f1.close()

    positions = []
    for pattern in ['<SDFIELD', '</SDFIELD', '<sdfield', '</sdfield' ]:
        p1 = data.find(pattern)
        while p1 >= 0:
           p2 = data.find('>', p1 + 1)
           if p2 >= 0:
               positions.append((p1,(p1, p2)))
           p1 = data.find(pattern, p1 + 1)
    positions.sort()

    if 0 and 'debug':
        from pprint import pprint
        if 1:
            for a,b in positions:
                p1,p2 = b
                print b, data[p1:p2+1]
        if 1:
            startpos = 0
            lendata = len(data)
            for p in positions:
                p1, p2 = p[1]
                print (startpos, p1), repr (data[startpos:startpos+20])
                print repr (data[p1:p2+1])
                startpos = p2 + 1

            print (startpos, lendata), repr (data[startpos:startpos+20])

    if f2name != '-':
        f2 = file(f2name, 'w')
    else:
        f2 = sys.stdout
    startpos = 0
    lendata = len(data)
    for p in positions:
        p1, p2 = p[1]
        f2.write(data[startpos:p1])
        startpos = p2 + 1

    f2.write(data[startpos:lendata])

    if f2name != '-':
        f2.close()

    return


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

        if not args.infile:
            msg = ("\nNote:\n"
                   "   '%(prog)s'\n"
                   "   needs module 'argparse' (Python >= 2.7) to handle commandline\n"
                   "   parameters. It seems that 'argparse' is not available. Provide\n"
                   "   module 'argparse' or hardcode parameters in the code instead.\n" % {'prog': sys.argv[0]} )
            print msg
            sys.exit(2)

    main(args.infile, args.outfile)
