# sclice_to_numbered_files.py
# mb, 2012-05-21, 2012-05-30, 2013-05-25

import codecs
import os
import shutil
import sys
import glob

ospj = os.path.join
ospe = os.path.exists

STARTNAME = 'Index'
rstfileext = '.rst'

depth = 3

from constants import CUTTER_MARK_IMAGES
from constants import SNIPPETS
from constants import SECTION_UNDERLINERS
section_underliners = ''.join(SECTION_UNDERLINERS)


HTML_THEME_PATH_IN_CONF_PY = """html_theme_path = ['../../../res/sphinx/themes/', '/usr/share/sphinx/themes/']"""

levels = [0 for i in range(depth+1)]
removeFromFilename = ''.join([ chr(i) for i in range(128) if chr(i).lower() not in 'abcdefghijklmnopqrstuvwxyz0123456789-_[]{}()+'])

def getCleanFileName(fname):
    fname = fname.encode('ascii','ignore')
    fname = fname.replace(' ','_')
    fname = fname.replace('/','_')
    fname = fname.replace('[','_')
    fname = fname.replace(']','')
    while '__' in fname:
        fname = fname.replace('__', '_')
    fname = fname.translate(None, removeFromFilename)
    return fname


def main(f1path, destdir):

    fnameimages = 'Images.txt'

    if not ospe(destdir):
        os.makedirs(destdir)

    if 1 and 'copy text following CUTTER_MARK_IMAGES to images.txt':
        f1 = codecs.open(f1path, 'r', 'utf-8-sig')
        f2name = ospj(destdir, fnameimages)
        f2 = codecs.open(f2name, 'w','utf-8-sig')
        skipping = True
        for line in f1:
            if skipping and line.startswith(CUTTER_MARK_IMAGES):
                skipping = False
            if not skipping:
                f2.write(line)
        f2.close()
        f1.close()

    toctree0 = '\n'.join([
        '',
        '.. toctree::',
        '   :maxdepth: 5',
        '   :titlesonly:',
        '   :glob:',
        '',
        '   %s',
        ''
        ])
    toctree = toctree0 % '*'


    f1 = codecs.open(f1path, 'r', 'utf-8-sig')
    f2path = ospj(destdir, STARTNAME) + rstfileext
    f2 = codecs.open(f2path, 'w', 'utf-8-sig')
    f2.write('.. include:: %s\n\n' % fnameimages)
    lines = []
    for line in f1:
        if line.startswith(CUTTER_MARK_IMAGES):
            break
        lines.append(line)
        while len(lines) >= 4:
            hot = len(lines[0].strip()) == 0
            hot = hot and (len(lines[1].strip()) != 0)
            hot = hot and (len(lines[2].strip()) != 0)
            hot = hot and (len(lines[3].strip()) == 0)
            hot = hot and (lines[1].rstrip('\r\n') <> (lines[1][0] * len(lines[1].rstrip('\r\n'))))
            hot = hot and (lines[2].rstrip('\r\n') == (lines[2][0] * len(lines[2].rstrip('\r\n'))))

            if hot:
                # switch to new file
                underliner = lines[2][0]
                p = section_underliners.find(underliner)
                if p > -1 and p < depth:

                    # close current file
                    if toctree:
                        f2.write(toctree)
                    if not f2 is sys.stdout:
                        f2.close()


                    levels[p] += 1
                    for i in range(p+1, depth+1):
                        levels[i] = 0
                    prefixparts = ['%02d'%levels[i] for i in range(p+1)]
                    f2name = '%s-%s' % ('-'.join(prefixparts), lines[1].strip())
                    f2name = getCleanFileName(f2name)

                    curdestdir = destdir
                    for i in range(len(prefixparts)):
                        curdestdir = os.path.join(curdestdir, ('-'.join(prefixparts[:i])))
                    if not ospe(curdestdir):
                        os.makedirs(curdestdir)
                    f2 = codecs.open(ospj(curdestdir, f2name) + rstfileext, 'w', 'utf-8-sig')

                    f2.write(SNIPPETS.for_your_information)






                    s = '.. include:: %sIncludes.txt\n' % ((len(prefixparts) * '../'),)
                    f2.write(s)
                    f2.write('.. include:: %s\n\n' % fnameimages)

                    if len(prefixparts) <= (depth-1):
                        prefix = '-'.join(prefixparts)
                        globexpr = prefix + '/*'
                        toctree = toctree0 % globexpr
                    else:
                        toctree = ''

            f2.write(lines[0])
            del lines[0]
    while lines:
        f2.write(lines[0])
        del lines[0]

    if not f2 is sys.stdout:
        f2.close()
    f1.close()

if __name__ == "__main__":
    if 0 and "testing at home":
        f1path = 'temp/_genesis/manual.rst'
        srcdir, srcfilef1name = os.path.split(f1path)
        destdir = 'temp/_genesis/temp'
        main(f1path, destdir)
    else:
        print "Please import and run main(...)"
