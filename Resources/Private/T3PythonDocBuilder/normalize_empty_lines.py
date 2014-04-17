# normalize_empty_lines.py
# mb, 2012-05-20, 2012-05-20
# This script has been placed in the public domain.
# No warrenties whatsoever. Use at your own risk.

import codecs
import sys

NL = '\n'
MAX_EMPTY_LINES = 2 or None

def main(f1name, f2name, maxemptylines=None):
    f1 = codecs.open(f1name, 'r', 'utf-8-sig')
    if f2name != '-':
        f2 = codecs.open(f2name, 'w', 'utf-8-sig')
    else:
        f2 = sys.stdout
    cnt = 0
    if not maxemptylines:
        for line in f1:
            f2.write(line)
    else:
        for line in f1:
            line = line.rstrip('\n')
            if line:
                while cnt > 0:
                    f2.write(NL)
                    cnt -= 1
                f2.write(line)
                f2.write(NL)
            else:
                if cnt < maxemptylines:
                    cnt += 1

    if not f2 == sys.stdout:
        f2.close()


if __name__ == "__main__":

    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print 'usage: python %s <infile.utf8.rst.txt> [<outfile.utf8.rst.txt>]' % sys.argv[0]#
        print '       Normalize maximum number of empty line following immediately'
        print '       upon each other. Number is: %s' % MAX_EMPTY_LINES
        sys.exit(2)

    f1name = sys.argv[1]
    if len(sys.argv) == 3:
        f2name = sys.argv[2]
    else:
        f2name = '-'
    main(f1name, f2name, MAX_EMPTY_LINES)
