# prepend_sections_with_labels.py
# mb, 2012-05-21, 2012-05-30, 2013-05-25

import codecs
import os
import sys

ospj = os.path.join
ospe = os.path.exists

from constants import CUTTER_MARK_IMAGES
from constants import SNIPPETS
from constants import SECTION_UNDERLINERS

asciiTable = ''.join([ chr(i) for i in range(256)])
alphaNumericTable = ''.join([chr(i) if chr(i).lower() in 'abcdefghijklmnopqrstuvwxyz0123456789-' else '-' for i in range(256)])

def sectionToLabel(aStr):
    aStr = aStr.strip()
    aStr = aStr.lower()
    aStr = aStr.encode('ascii','ignore')
    aStr = aStr.translate(alphaNumericTable)
    while '----' in aStr:
        aStr = aStr.replace('----', '-')
    while '--' in aStr:
        aStr = aStr.replace('--', '-')
    aStr = aStr.strip('-')
    return aStr


def processRstFile(f1path):
    f2path = f1path + '.temp.rst'
    f1 = codecs.open(f1path, 'r', 'utf-8-sig')
    f2 = codecs.open(f2path, 'w', 'utf-8-sig')
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
                label = sectionToLabel(lines[1])
                f2.write(lines[0])
                f2.write('.. _%s:\n\n' % label)
                f2.write(lines[1])
                f2.write(lines[2])
                del lines[0:3]
            else:
                f2.write(lines[0])
                del lines[0]

    while lines:
        f2.write(lines[0])
        del lines[0]

    if not f2 is sys.stdout:
        f2.close()
    f1.close()

    os.remove(f1path)
    os.rename(f2path, f1path)

def main(startDir):
    for path, dirs, files in os.walk(startDir):
        for fname in files:
            stem, ext = os.path.splitext(fname)
            if ext == '.rst':
                f1path = ospj(path, fname)
                processRstFile(f1path)

if __name__ == "__main__":
    if 0 and "testing at home":
        startDir = r'D:\T3PythonDocBuilder\temp\t3pdb\Documentation'
        main(startDir)
    else:
        print "Please import and run main(...)"
