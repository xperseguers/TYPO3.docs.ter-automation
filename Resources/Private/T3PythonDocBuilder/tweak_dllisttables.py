# tweak_dllisttables.py
# mb, 2012-05-21, 2013-05-29, 2013-06-11

import codecs
import os
import sys
import re
import prepend_sections_with_labels

ospj = os.path.join
ospe = os.path.exists

from constants import CUTTER_MARK_IMAGES
from constants import SNIPPETS
from constants import SECTION_UNDERLINERS

CURRENT_UNDERLINER = '*'

def tweakTableRow(lines):
    indentLevel = lines[0].find('..')
    indentBlanks3 = ' ' * (indentLevel + 3)
    indentBlanks9 = ' ' * (indentLevel + 9)

    # check 1: Do we have a stupid header row?
    rowIsMeaningful = False
    dt = None
    dd = None
    for i, line in enumerate(lines):
        if i==0 or line.strip()=='':
            continue
        line = line.rstrip()
        if dt is None:
            m = re.match(indentBlanks3 + '(.+)', line)
            if m:
                dt = m.group(1).lower().replace(':','')
            else:
                rowIsMeaningful = True
        elif dd is None:
            m = re.match(indentBlanks9 + '(.+)', line)
            if m:
                dd = m.group(1).lower().replace(':','')
                if dt == dd:
                    dt = None
                    dd = None
            else:
                rowIsMeaningful = True
        else:
            rowIsMeaningful = True
        if rowIsMeaningful:
            break
    else:
        lines = []
        return lines


    # check 2, manipulation: insert label and header
    p = SECTION_UNDERLINERS.index(CURRENT_UNDERLINER)
    underliner = SECTION_UNDERLINERS[p+1]

    if 0:
        print
        for line in lines:
            print repr(line.rstrip())
        x = 10

    dt = None
    dd = None
    property = ''
    for i, line in enumerate(lines):
        if i==0 or line.strip()=='':
            continue
        line = line.rstrip()
        if dt is None:
            m = re.match(indentBlanks3 + '(.+)', line)
            if m:
                dt = True
            else:
                break
        elif dd is None:
            m = re.match(indentBlanks9 + '(.+)', line)
            if m:
                property = m.group(1)
            break
        else:
            break

    if not property:
        property = '((Unknown Property))'

    if property:
        label = prepend_sections_with_labels.sectionToLabel(property)
        s = \
          '\n'\
          '.. _%s:\n'\
          '\n'\
          '%s\n'\
          '%s\n'\
          '\n' % (label, property, underliner * len(property))
        lines.insert(0, s)

    return lines


def processRstFile(f1path):
    global CURRENT_UNDERLINER
    withinTable = False
    f2path = f1path + '.temp.txt'
    f1 = codecs.open(f1path, 'r', 'utf-8-sig')
    f2 = codecs.open(f2path, 'w', 'utf-8-sig')
    state = None
    indentLen = 0
    indentStr = ''
    lines = []
    for line in f1:

        if withinTable:
            if state == 'before table-row':
                if line.strip().startswith('.. container:: table-row'):
                    state = 'before first cell'
                    lines.append(line)
                else:
                    f2.write(line)
            elif state == 'before first cell':
                if not line.strip():
                    lines.append(line)
                else:
                    m = re.match('   (.*)', line[indentLen:])
                    if m:
                        state = 'within row'
                        property = m.group(1)
                        lines.append(line)
            elif state == 'within row':
                if not line.strip():
                    lines.append(line)
                elif line[0:3] == '   ':
                    lines.append(line)
                else:
                    state = 'at end of row'
                    lines = tweakTableRow(lines)
                    for aline in lines:
                        f2.write(aline)
                    lines = []
                    if line.strip().startswith('.. ###### END~OF~TABLE ######'):
                        withinTable = False
                        f2.write(line)
                    elif line.strip().startswith('.. container:: table-row'):
                        state = 'before first cell'
                        lines.append(line)
                    else:
                        withinTable = False
                        f2.write(line)
        else:
            lines.append(line)
            while len(lines) >= 4:
                hot = len(lines[0].strip()) == 0
                hot = hot and (len(lines[1].strip()) != 0)
                hot = hot and (len(lines[2].strip()) != 0)
                hot = hot and (len(lines[3].strip()) == 0)
                hot = hot and (lines[1].rstrip('\r\n') <> (lines[1][0] * len(lines[1].rstrip('\r\n'))))
                hot = hot and (lines[2].rstrip('\r\n') == (lines[2][0] * len(lines[2].rstrip('\r\n'))))
                if hot:
                    CURRENT_UNDERLINER = lines[2][0]
                    del lines[0:3]
                else:
                    del lines[0]

            if line.strip().startswith('.. ### BEGIN~OF~TABLE ###'):
                withinTable = True
                state = 'before table-row'
                indentLen = line.find('.. ### BEGIN~OF~TABLE ###')
                lines = []
                if 0:
                    print f1path
            f2.write(line)


    while lines:
        # f2.write(lines[0])
        del lines[0]

    if not f2 is sys.stdout:
        f2.close()
    f1.close()

    if 1:
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
    if 1 and "testing at home":
        startDir = r'D:\T3PythonDocBuilder\temp\t3pdb\Documentation'
        main(startDir)
    else:
        print "Please import and run main(...)"
