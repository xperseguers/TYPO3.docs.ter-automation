import os
import shutil
import subprocess

def main(f0path, f2path):

    f0dir, f0name = os.path.split(f0path)
    f0stem, f0ext = os.path.splitext(f0name)
    f2dir, f2name = os.path.split(f2path)
    f2stem, f2ext = os.path.splitext(f2name)

    if f0stem.lower() == f2stem.lower():
        f1path = f0path
    else:
        # The OpenOffice writer creates an <outfile> with the same name as <infile>.
        # The desired <outfile> name is different from the actual <infile> name.
        # To fix this we make a copy of <infile> 'f0path' to 'f1path' thereby
        # renaming the file. Afterwards we take 'f1path' as <infile>.
        # Example:
        #   f0path: ./workspaces_manual.sxw
        #   f1path: ./temp/t3pdc/manual.sxw
        #   f2path: ./temp/t3pdc/manual.html

        f1path = os.path.join(f2dir, f2stem + f0ext)
        shutil.copyfile(f0path, f1path)

    f1dir, f1name = os.path.split(f1path)
    f1stem, f1ext = os.path.splitext(f1name)

    # still untested! 'soffice' must be in the path
    cmd = ' '.join([
        'soffice',
        '--headless',
        '-convert-to html',
        '-outdir', f2dir,
        f1path,
        ])

    subprocess.call(cmd, shell=True)
    if os.path.exists(f2path):
        retCode, msg = 0, 'ok'
    else:
        retCode, msg = 1, "Could not convert '%s' to '%s' by command '%s'" % (
            f0name, f2name, cmd)
    return retCode, msg



if __name__ == "__main__":
    from sys import argv, exit

    if len(argv) < 3 or len(argv) > 3:
        print "USAGE: python %s <input-file> <output-file>" % argv[0]
        exit(255)
    if not os.path.isfile(argv[1]):
        print "no such input file: '%s'" % argv[1]
        exit(1)

    retCode, msg = main(argv[1], argv[2])

