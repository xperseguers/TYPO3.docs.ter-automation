# write_sphinx_structure.py
# mb, 2012-05-21, 2013-08-02

# mostly a cruel hack ...

import os
import sys
import re
import codecs
import shutil
import glob
from pprint import pprint
import slice_to_numbered_files


ospj = os.path.join
ospe = os.path.exists


class DocumentationMaker:

    def __init__(self, arg):
        self.arg = arg
        self.eliminateFirstLevel = None


    def findRstFiles(self, srcdir, startpos):
        result = []
        for curdir, dirs, files in os.walk(srcdir):
            files.sort()
            dirs.sort()
            for afile in files:
                if afile.endswith('.rst'):
                    fpath = os.path.join(curdir, afile)
                    fpath = fpath.replace('\\', '/')
                    result.append(fpath[startpos:])
        return result

    def getTocTreeEntries(self, relpath2, f2name, sublevels, listOfOldNew):
        result = []
        for f1relpathx, relpath2x, f2namex, sublevelsx in listOfOldNew:
            if relpath2x.startswith(relpath2) and (sublevelsx - sublevels) == 1:
                subpath = relpath2x.split('/')[-1]
                if subpath:
                    f2relpathx = ospj(subpath, f2namex).replace('\\', '/')
                else:
                    f2relpathx = f2namex
                if f2relpathx.startswith('/'):
                    f2relpathx = f2relpathx[1:]
                if f2relpathx.endswith('.rst'):
                    f2relpathx = f2relpathx[:-len('.rst')]
                result.append(f2relpathx)
        return result

    def buildLookUpTable1(self, rstfiles, capitalize):
        D = {}
        for afile in rstfiles:
            consumed = 0
            if afile.lower() == 'index.rst':
                k = ''
                v = afile[:-4]
                v2 = v
                if capitalize:
                    v2 = v2.capitalize()
                D[k] = (v,v2)
                consumed = 1
            else:
                parts = afile.split('/')
                m = re.match('^(?P<number>(\d\d-)+)(?P<name>.*)\.rst$', parts[-1])
                if m:
                    k = m.group('number')
                    v = m.group('name')
                    v2 = v
                    # remove something like 'img-57_' at the beginning
                    triedmatch = False
                    m = True
                    while m:
                        if triedmatch:
                            v2 = m.group(1)
                        else:
                            triedmatch = True
                        m = re.match('^img[-_]\d+[-_](.*)', v2)
                    if capitalize:
                        v2 = ''.join([s.capitalize() for s in v2.split('_')])
                    D[k] = (v,v2)
                    consumed = 1
            if not consumed:
                print "Can't handle file '%s'" % afile
                sys.exit(2)
        return D


    def makeListOfOldNew(self, D, capitalize):
        listOfOldNew =[]
        keys = sorted(D.keys())
        for k in keys:
            f1name = k + D[k][0] + '.rst'
            relpath1 = []
            relpath2 = []
            parts = k.strip('-').split('-')
            for i in range(len(parts)):
                k2 = '-'.join(parts[:i+1])
                if k2:
                    k2 += '-'

                # destination file name
                v2 = D[k2][1]
                v2 = v2.replace('[', '-')
                v2 = v2.replace(']', '')
                relpath1.append(k2.strip('-'))
                relpath2.append(v2)

            f2name = 'index.rst'
            if capitalize:
                f2name = f2name.capitalize()
            if relpath2 == ['index'] or relpath2 == ['Index']:
                relpath2 = ['']
                sublevels = 0
            else:
                sublevels = len(relpath2)

            relpath1 = relpath1[:-1]
            relpath1= '/'.join(relpath1)
            relpath2= '/'.join(relpath2)
            if not capitalize:
                relpath2 = relpath2.lower()
            relpath2 = relpath2.replace('_', '-')

            f1relpath = ospj(relpath1, f1name).replace('\\', '/')
            f2relpath = ospj(relpath2, f2name).replace('\\', '/')
            vtuple = (f1relpath, relpath2, f2name, sublevels)
            if 0:
                print vtuple
            listOfOldNew.append(vtuple)
        return listOfOldNew


    def main(self, srcdir, destdir, srcdirimages, verbose=None, capitalize=True):
        NL = '\n'
        srcdirlen = len(srcdir)
        fnameimages = 'Images.txt'

        slice_to_numbered_files.main(self.arg.f2path_rst, self.arg.safetempdir_sliced)
        os.makedirs(self.arg.f2path_documentation)

        rstfiles = self.findRstFiles(srcdir, srcdirlen+1)
        D = self.buildLookUpTable1(rstfiles, capitalize)

        cnt = 0
        for k in D.keys():
            if len(k) == 3:
                cnt += 1

        # for most manuals its better to shorten the up path of images
        # by one '../' as that better fits the manual corrections
        # that follow. This happens when there is just one subfolder
        # at the top. All files that folder should then be move up
        # one level and Index.rst and Images.txt should be manually
        # merged
        if cnt == 1:
            sublevel_images_correction = -1
            self.eliminateFirstLevel = True
        else:
            sublevel_images_correction = 0
            self.eliminateFirstLevel = False


        listOfOldNew = self.makeListOfOldNew(D, capitalize)


        if 1 and 'copy':

            # copy source files to their new destinations
            # thereby tweaking the contents of the destination file

            cnt = 0
            for f1relpath, relpath2, f2name, sublevels in listOfOldNew:
                cnt += 1
                f2relpath = ospj(relpath2, f2name).replace('\\', '/')
                if f2relpath.startswith('/'):
                    f2relpath = f2relpath[1:]

                f1path = ospj(srcdir, f1relpath)
                f2path = ospj(destdir, f2relpath)
                if 0:
                    print 1, f1path
                    print 2, f2path
                    print
                f2destdir = os.path.split(f2path)[0]
                if not ospe(f2destdir):
                    os.makedirs(f2destdir)

                f1 = codecs.open(f1path, 'r', 'utf-8-sig')
                f2 = codecs.open(f2path, 'w', 'utf-8-sig')
                if verbose:
                    print f1path
                    print f2path

                parts = relpath2.split('/')

                skiptherest = False
                skipblock = False
                for line in f1:
                    line = line.rstrip('\n')
                    if skiptherest:
                        break
                    if line in [u'\ufeff', u'\r']:
                        continue
                    if skipblock:
                        if line and (line[0] != ' '):
                            skipblock = False
                        else:
                            continue
                    for item in ['.. sectnum:', '.. contents:']:
                        if line.startswith(item):
                            skipblock = True
                            break
                    if skipblock:
                        continue
                    if line.startswith('.. toctree'):
                        skiptherest = True
                        break
                    f2.write(line)
                    f2.write(NL)

                # now add the ..toctree directive
                tte = self.getTocTreeEntries(relpath2, f2name, sublevels, listOfOldNew)
                if tte:
                    s = (
                        '.. toctree::\n'
                        '   :maxdepth: 5\n'
                        '   :titlesonly:\n'
                        '   :glob:\n'
                        '\n' )
                    f2.write(s)
                    for e in tte:
                        f2.write('   %s%s' % (e, NL))
                    if not relpath2 and f2name == 'Index.rst':
                        f2.write('   Targets\n')
                    f2.write('\n')
                f2.close()
                f1.close()

                if 1:
                    # which images are referenced in the just written file?
                    f2 = codecs.open(f2path, 'r', 'utf-8-sig')
                    data = f2.read()
                    f2.close()
                    usedimages = re.findall('\|img-\d+\|', data)
                    del data
                    if verbose:
                        print usedimages

                if 1:
                    if usedimages:
                        src = ospj(srcdir, fnameimages)
                        dest = ospj(f2destdir, fnameimages)
                        if verbose:
                            print src
                            print dest
                        if 1:
                            f1 = codecs.open(src, 'r', 'utf-8-sig')
                            f2 = codecs.open(dest, 'w', 'utf-8-sig')
                            skipping = True
                            for line in f1:
                                if skipping:
                                    r = re.findall('\|img-\d+\|', line)
                                    if r and r[0] in usedimages:
                                        skipping = False
                                if not skipping:
                                    if capitalize:
                                        line = line.replace('image:: ', 'image:: %sImages/' % ('../' * (sublevels + sublevel_images_correction)))
                                    else:
                                        line = line.replace('image:: ', 'image:: %simg/' % ('../' * (sublevels + sublevel_images_correction)))
                                    f2.write(line)
                                    if line.strip() == '':
                                        skipping = True
                            f2.close()
                            f1.close()

                    if not usedimages:
                        data = file(f2path).read()
                        data = data.replace('.. include:: %s' % fnameimages, '')
                        f2 = file(f2path, 'wb')
                        f2.write(data)
                        f2.close()


            if 1:
                # copy folders if present
                for relpath in ['_static', '_templates', 'img', 'images', ]:
                    src = ospj(srcdir, relpath)
                    dest = ospj(destdir, relpath)
                    if ospe(src):
                        if ospe(dest):
                            shutil.rmtree(dest)
                        shutil.copytree(src, dest)
            if 1:
                # copy non *.rst files from rootfolder if present
                files = os.listdir(srcdir)
                for fname in files:
                    src = ospj(srcdir,fname)
                    if os.path.isfile(src) and not src.endswith('.rst') and not src.endswith(fnameimages):
                        dest = ospj(destdir, fname)
                        shutil.copyfile(src, dest)
            if 1:
                # copy image material (manual_html_*) to img/
                files = glob.glob(ospj(srcdirimages, 'manual_html_*'))
                for src in files:
                    fname = os.path.split(src)[1]
                    destdirimg = ospj(destdir, 'Images')
                    if not ospe(destdirimg):
                        os.makedirs(destdirimg)
                    dest = ospj(destdirimg, fname)
                    if verbose:
                        print src
                        print dest
                        print
                    shutil.copyfile(src, dest)


    def addResourceFiles(self):
        # res files
        srcdir = ospj('resources', 'default_files', 'Documentation')
        if not ospe(srcdir) or not os.path.isdir(srcdir):
            return 0, 'no resource files found'
        srcdirlen = len(ospj(srcdir,'abc')) - 3
        for relpath, dirs, files in os.walk(srcdir):
            destdir = ospj(self.arg.f2path_documentation, relpath[srcdirlen:])
            for afile in files:
                if afile.startswith('default_'):
                    if not ospe(destdir):
                        os.makedirs(destdir)
                    srcfile = ospj(relpath, afile)
                    destfile = ospj(destdir, afile[8:])
                    shutil.copyfile(srcfile, destfile)

    def adjustForCorrection(self):
        if not self.eliminateFirstLevel:
            return

        subdir = None
        for item in os.listdir(self.arg.f2path_documentation):
            if os.path.isdir(ospj(self.arg.f2path_documentation, item)):
                if not (item in ['Images', '_make']):
                    subdir = item
                    break
        if subdir:
            srcImages = ospj(self.arg.f2path_documentation, 'Images')
            destImages = ospj(self.arg.f2path_documentation, subdir, 'Images')
            if os.path.exists(srcImages):
                os.rename(srcImages, destImages)

        f1path = ospj(self.arg.f2path_documentation, 'Images.txt')
        if ospe(f1path):
            f1 = codecs.open(f1path, 'r', 'utf-8-sig')
            data = f1.read()
            f1.close()
            data = data.replace('image:: Images/',  'image:: %s/Images/' % subdir)
            f2 = codecs.open(f1path, 'w', 'utf-8-sig')
            f2.write(data)
            f2.close()




def main(arg):
    DM = DocumentationMaker(arg)
    DM.main(
        arg.safetempdir_sliced,
        arg.f2path_documentation,
        arg.srcdirimages,
        verbose=0)
    DM.addResourceFiles()
    DM.adjustForCorrection()

    retCode, msg = 0, 'ok'
    return retCode, msg


if 0 and __name__ == "__main__":
    if 0 and "testing at home":
        srcdir  = 'D:/TYPO3-Documentation/t3doc-srv123-mbless/git.typo3.org/Documentation/TYPO3/Reference/Typoscript.git/Documentation/_not_versioned/_genesis/temp'
        destdir = 'D:/TYPO3-Documentation/t3doc-srv123-mbless/git.typo3.org/Documentation/TYPO3/Reference/Typoscript.git/Documentation\\source'
        srcdirimages = 'D:/TYPO3-Documentation/t3doc-srv123-mbless/git.typo3.org/Documentation/TYPO3/Reference/Typoscript.git/Documentation/_not_versioned/_genesis'
    else:
        print "please import this script and run main(...)"

if 0 and __name__ == "__main__":
    if 1 and "testing at home":
        class Namespace(object):
            """Simple object for storing attributes."""

            def __init__(self, **kwargs):
                for name in kwargs:
                    setattr(self, name, kwargs[name])

        arg = Namespace()
        arg.f2path_rst = 'temp\\t3pdb\\manual.t3flt.rst'
        arg.safetempdir_sliced = 'temp2\\t3pdb\\_sliced'
        arg.f2path_documentation = 'temp2\\t3pdb\\Documentation'
        arg.srcdirimages = 'temp2\\t3pdb'
        arg.resdir = 'resources'


        retCode, msg = main(arg)
