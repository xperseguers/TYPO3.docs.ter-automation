# remove_first_t3fieldlisttable_row.py
# mb, 2012-05-21, 2012-05-30, 2013-05-29

import codecs
import os
import sys
import re

ospj = os.path.join
ospe = os.path.exists

from constants import CUTTER_MARK_IMAGES
from constants import SNIPPETS
from constants import SECTION_UNDERLINERS


def keepOrDropFirstRow(lines):
    drop = True
    name = None
    for line in lines:
        if not line.strip():
            continue
        if not drop:
            break
        if not name:
            m = re.match('\s*-\s+:(.+):\s*', line)
            if m:
                name = m.group(1)
            else:
                m = re.match('\s+:(.+):\s*', line)
                if m:
                    name = m.group(1)
                else:
                    drop = False
        else:
            v = line
            v = v.replace(':', '')
            v = v.strip()
            v = v.lower()
            if not v == name.lower():
                drop = False
            else:
                name = None
    if drop and not name:
        lines = []
    return lines




def processRstFile(f1path):
    withinT3FieldListTable = False
    f2path = f1path + '.temp.rst'
    f1 = codecs.open(f1path, 'r', 'utf-8-sig')
    f2 = codecs.open(f2path, 'w', 'utf-8-sig')
    lines = []
    state = None
    indentLen = 0
    indentStr = ''
    for line in f1:
        if withinT3FieldListTable:
            if state == 'before':
                if line.startswith(indentStr + ' - '):
                    lines.append(line)
                    state = 'within'
                else:
                    f2.write(line)

            elif state == 'within':
                if line.startswith(indentStr + ' - '):
                    state = 'atNextRow'
                    lines = keepOrDropFirstRow(lines)
                    while lines:
                        f2.write(lines[0])
                        del lines[0]
                    f2.write(line)
                    withinT3FieldListTable = False
                else:
                    lines.append(line)

        else:
            m = re.match('([ ]*)(\.\. t3-field-list-table::)(.*)', line)
            if m:
                withinT3FieldListTable = True
                state = 'before'
                indentStr = m.group(1)
                indentLen = len(indentStr)
            f2.write(line)

    while lines:
        f2.write(lines[0])
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
    if 0 and "testing at home":
        startDir = r'D:\T3PythonDocBuilder\temp\t3pdb\Documentation'
        main(startDir)
    else:
        print "Please import and run main(...)"
