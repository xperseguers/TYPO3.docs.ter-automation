#!/bin/bash

# ------------------------------------------------------
# Builds a Sphinx project for TYPO3 projects
#
# Exit Status:
#
# 1: Configuration file cron_rebuild.conf was not found
# 2: Invalid Git directory for the project
# 3: Non-existing project directory
# 4: No documentation found
# 5: No success for include file check
# ------------------------------------------------------

# Retrieve current script directory (as absolute path)
BIN_DIRECTORY=$(dirname $(readlink "$0"))

# Configure tools for BSD or GNU
stat --version >/dev/null 2>&1
if [ $? -eq 0 ]; then
    # GNU
    STAT_FORMAT="stat --format=%Y"
    SED_EXTENDED="sed -r"
else
    # BSD
    STAT_FORMAT="stat -f %m"
    SED_EXTENDED="sed -E"
fi

# Retrieve current directory (as absolute path)
MAKE_DIRECTORY=$(unset CDPATH && cd "$(dirname "$0")" && echo $PWD)
pushd $MAKE_DIRECTORY >/dev/null

if [ ! -r "cron_rebuild.conf" ]; then
    echo "Cannot find configuration file cron_rebuild.conf in $MAKE_DIRECTORY" 2>&1
    exit 1
fi

. cron_rebuild.conf

# The list of supported languages by Sphinx is available
# on http://sphinx-doc.org/latest/config.html#intl-options
#
# BEWARE: 1) of space at the end of the string
#         2) "en" is not included because we map it to "default" instead
SPHINX_LANGUAGES="bn ca cs da de es et eu fa fi fr hr hu it ja ko lt lv nb_NO ne nl pl pt_BR ru sk sl sv tr uk_UA zh_CN zh_TW "

# ------------------------------------------------------
#
# Returns the "language" supported by Sphinx from a
# given user's locale (e.g., "fr_FR" will return "fr").
#
# The list of supported languages by Sphinx is available
# on http://sphinx-doc.org/latest/config.html#intl-options
# ------------------------------------------------------
function findsphinxlanguage() {
    local USERLOCALE="$1"

    echo "$SPHINX_LANGUAGES" | grep "$USERLOCALE " >/dev/null
    if [ $? -eq 0 ]; then
        # User's locale exists as this in Sphinx
        echo -n $USERLOCALE
    else
        # Try with the 2-letter language code only
        local USERLANGUAGE=$(echo $USERLOCALE | sed 's/_..$//')
        echo "$SPHINX_LANGUAGES" | grep "$USERLANGUAGE " >/dev/null
        if [ $? -eq 0 ]; then
            echo -n $USERLANGUAGE
        else
            echo -n default
        fi
    fi
}

# ------------------------------------------------------
#
# The cron job sends an email. Include a bit of information
# at the top so we know what project is being build.
#
# ------------------------------------------------------
function projectinfo2stdout() {
    echo "=================================================="
    echo "Project   : $PROJECT"
    echo "Version   : $VERSION"
    echo "GitDir    : $GITDIR"
    echo "Repository: $GITURL"
}

# ------------------------------------------------------
#
# Lazily move files using hard-linking to other versions
# of the same files whenever possible.
#
# ------------------------------------------------------
function lazy_mv() {
    local FROM_DIR="$1"
    local TO_DIR="$2"
    local PARENT_DIR="$(dirname $2)"

    # Move directory to its final place
    if [ -d "$PARENT_DIR" ]; then
        rm -rf $TO_DIR
    else
        mkdir $PARENT_DIR
    fi
    mv $FROM_DIR $TO_DIR

    # Find duplicates one level higher and replace them with hard-links
    fdupes -rLq $TO_DIR/..
}

# ------------------------------------------------------
#
# This function takes care of compiling the project
# as PDF, removing any intermediate LaTeX files.
#
# ------------------------------------------------------
function compilepdf() {
    local EXITCODE
    local PDFFILE
    local TARGETPDF

    grep -A3 latex_elements $MAKE_DIRECTORY/10+20+30_conf_py.yml | egrep "^    preamble: \\\\usepackage{typo3}" >/dev/null
    if [ $? -ne 0 ]; then
        echo "PDF rendering is not configured, skipping."
        return
    fi

    make -e latex
    # Fix generated Makefile for batch processing
    sed -i"" 's/pdflatex /pdflatex -interaction=nonstopmode -halt-on-error /' $BUILDDIR/latex/Makefile
    # Fix use of straight single quotes in source code
    perl -i -pe 'BEGIN{undef $/;} s/(\\makeatother.*?\\begin\{document\})/\\def\\PYGZsq{\\textquotesingle}\n\1/smg' $BUILDDIR/latex/$PROJECT.tex
    make -C $BUILDDIR/latex all-pdf
    EXITCODE=$?

    PDFFILE=$BUILDDIR/latex/$PROJECT.pdf
    if [ "$PACKAGE_LANGUAGE" == "default" ]; then
        TARGETPDF=manual.$PROJECT-$VERSION.pdf
    else
        TARGETPDF=manual.$PROJECT-$VERSION.${PACKAGE_LANGUAGE}.pdf
    fi

    if [ $EXITCODE -ne 0 ]; then
        # Store log into pdflatex.txt, may be useful to investigate
        cat $BUILDDIR/latex/*.log >> $MAKE_DIRECTORY/pdflatex.txt
        echo "Could not compile as PDF, skipping."
    elif [ ! -f "$PDFFILE" ]; then
        EXITCODE=1
        echo "Could not find output PDF, skipping."
    else
        # Move PDF to a directory "_pdf" (instead of "latex")
        mkdir $BUILDDIR/_pdf
        mv $PDFFILE $BUILDDIR/_pdf/$TARGETPDF

        # Create a .htaccess that redirects everything to the real PDF
        # Remove "/home/mbless/public_html" at the beginning
        TARGETDIR=$(echo $ORIG_BUILDDIR | cut -b25-)/_pdf

        pushd $BUILDDIR/_pdf >/dev/null
        echo "RewriteEngine On"                                    >  .htaccess
        echo "RewriteCond %{REQUEST_FILENAME} !-f"                 >> .htaccess
        echo "RewriteRule ^(.*)\$ $TARGETDIR/$TARGETPDF [L,R=301]" >> .htaccess
        popd >/dev/null
    fi

    # Remove LaTeX intermediate files
    rm -rf $BUILDDIR/latex

    return $EXITCODE
}

# ------------------------------------------------------
#
# This function takes care of packaging the
# HTML documentatin as a zip file and recreates
# the index of available packages.
#
# ------------------------------------------------------
function packagedocumentation() {
    local PACKAGEDIR
    if [ "${PACKAGE_LANGUAGE}" == "default" ]; then
        PACKAGEDIR=$ORIG_BUILDDIR/../packages
    else
        PACKAGEDIR=$ORIG_BUILDDIR/../../packages
    fi
    local LANGUAGE_SEGMENT=$(echo ${PACKAGE_LANGUAGE//_/-} | tr '[A-Z]' '[a-z]')
    local ARCHIVE=${PROJECT}-${VERSION}-${LANGUAGE_SEGMENT}.zip

    rm -rf /tmp/$PACKAGE_KEY /tmp/$ARCHIVE
    mkdir -p /tmp/$PACKAGE_KEY/$PACKAGE_LANGUAGE/html
    cp -r $BUILDDIR/* /tmp/$PACKAGE_KEY/$PACKAGE_LANGUAGE/html

    # Move PDF if needed
    if [ -d "$BUILDDIR/_pdf" ]; then
        mkdir -p /tmp/$PACKAGE_KEY/$PACKAGE_LANGUAGE/pdf
        pushd /tmp/$PACKAGE_KEY/$PACKAGE_LANGUAGE > /dev/null
        find html/_pdf/ -type f -name \*.pdf -exec mv {} pdf/ \;
        rm -rf html/_pdf/
        popd >/dev/null
    fi

    pushd /tmp >/dev/null
    zip -r -9 -q $ARCHIVE $PACKAGE_KEY
    mkdir -p $PACKAGEDIR
    mv $ARCHIVE $PACKAGEDIR/
    rm -rf /tmp/$PACKAGE_KEY
    popd >/dev/null

    # Create documentation pack index
    pushd $PACKAGEDIR >/dev/null
    rm -f packages.xml
    touch packages.xml

    echo -e "<?xml version=\"1.0\" standalone=\"yes\" ?>"                   >> packages.xml
    echo -e "<documentationPackIndex>"                                      >> packages.xml
    echo -e "\t<meta>"                                                      >> packages.xml
    echo -e "\t\t<timestamp>$(date +"%s")</timestamp>"                      >> packages.xml
    echo -e "\t\t<date>$(date +"%F %T")</date>"                             >> packages.xml
    echo -e "\t</meta>"                                                     >> packages.xml
    echo -e "\t<languagePackIndex>"                                         >> packages.xml

    for p in $(find . -name \*.zip | sort);
    do
            local _VERSION=$(echo $p | $SED_EXTENDED "s/.*-([0-9.]*|latest)-([a-z-]*)\.zip\$/\1/")
            local _LANGUAGE=$(echo $p | $SED_EXTENDED "s/.*-([0-9.]*|latest)-([a-z-]*)\.zip\$/\2/")
            if [ "$_LANGUAGE" != "default" ]; then
                _LANGUAGE=$(echo $_LANGUAGE | sed 's/..$/\U&/' | sed 's/-/_/')
            fi
            echo -e "\t\t<languagepack version=\"$_VERSION\" language=\"$_LANGUAGE\">" >> packages.xml
            echo -e "\t\t\t<md5>$(md5sum $p | cut -d" " -f1)</md5>"         >> packages.xml
            echo -e "\t\t</languagepack>"                                   >> packages.xml
    done

    echo -e "\t</languagePackIndex>"                                        >> packages.xml
    echo -e "</documentationPackIndex>"                                     >> packages.xml

    popd >/dev/null
}

# ------------------------------------------------------
#
# Checks if rebuild is needed by comparing a checksum
# of the documentation files with the last build's
# checksum.
#
# Returns 1 if rebuild is needed, otherwise 0.
#
# ------------------------------------------------------
function rebuildneeded() {
    if [ -r "$T3DOCDIR/Index.rst" ]; then
        local CHECKSUM=$(find "$T3DOCDIR" -type f -exec md5sum {} \; | md5sum | awk '{ print $1 }')
    elif [ -r "$T3DOCDIR/README.rst" ]; then
        local CHECKSUM=$(md5sum "$T3DOCDIR/README.rst" | awk '{ print $1 }')
    else
        # No documentation, should not happen
        return 0
    fi

    # allow a rebuild after 24 hours even it the checksum did not change
    if [ -r "$MAKE_DIRECTORY/build.checksum" ] && [ `$STAT_FORMAT "$MAKE_DIRECTORY/build.checksum"` -le $(( `date +%s` - 24*60*60)) ]; then
        rm "$MAKE_DIRECTORY/build.checksum"
    fi
    
    if [ ! -r "$MAKE_DIRECTORY/build.checksum" ]; then
        # Never built
        echo $CHECKSUM > "$MAKE_DIRECTORY/build.checksum"
        return 1
    else
        local LAST_CHECKSUM=$(cat "$MAKE_DIRECTORY/build.checksum")
    fi

    if [ "$LAST_CHECKSUM" == "$CHECKSUM" ]; then
        return 0
    else
        echo $CHECKSUM > "$MAKE_DIRECTORY/build.checksum"
        return 1
    fi
}

function renderdocumentation() {
    local BASE_DIR="$1"
    T3DOCDIR="$2"
    local IS_TRANSLATION=$3
    local SPHINXCODE=$(findsphinxlanguage $PACKAGE_LANGUAGE)

    echo
    echo "======================================================"
    echo "Now rendering language $PACKAGE_LANGUAGE"
    echo "======================================================"
    echo

    if [ "$SPHINXCODE" != "default" ]; then
        # We want localized static labels with Sphinx
        # and LaTeX
        export LANGUAGE=$SPHINXCODE
    fi

    # cron: add to stdout which goes via mail to Martin
    #cat "$MAKE_DIRECTORY"/included-files-check.log.txt

    BACKUP_BUILDDIR=$BUILDDIR

    if [ $IS_TRANSLATION -eq 1 ]; then
        local LAST_SEGMENT=$(basename $BUILDDIR)
        local LANGUAGE_SEGMENT=$(echo ${PACKAGE_LANGUAGE//_/-} | tr '[A-Z]' '[a-z]')
        BUILDDIR=$BUILDDIR/../$LANGUAGE_SEGMENT/$LAST_SEGMENT

        # Override Settings.yml (conf.py is hardcoded to ./Documentation/Settings.yml)
        if [ -r "$T3DOCDIR/Settings.yml" ]; then
            cp $T3DOCDIR/Settings.yml $BASE_DIR/
        fi
    fi

    # Replace all slashes to dashes for a temporary build directory name
    local ORIG_BUILDDIR=$BUILDDIR
    BUILDDIR=/tmp/${BUILDDIR//[\/.]/-}

    # Export variables to be used by Makefile later on
    export BUILDDIR
    export T3DOCDIR

    cd $MAKE_DIRECTORY
    rm -rf $BUILDDIR
    #make -e clean
    make -e html

    # Prepare PDF using LaTeX
    compilepdf

    if [ "$PACKAGE_ZIP" == "1" ]; then
        # Package the documentation
        packagedocumentation
    fi

    # Create other versions of the documentation
    # make -e gettext
    # make -e json
    make -e singlehtml
    # make -e dirhtml

    ln -s $MAKE_DIRECTORY $BUILDDIR/_make

    # Make simple README documentation accessible
    pushd $BUILDDIR >/dev/null
    if [ ! -r "Index.html" ] && [ -r "README.html" ]; then
        ln -s README.html Index.html
    fi
    popd >/dev/null

    # Switch rendered documentation in public_html
    lazy_mv $BUILDDIR $ORIG_BUILDDIR
    chgrp -R www-default $ORIG_BUILDDIR
    if [ ! -r "$ORIG_BUILDDIR/../.htaccess" ]; then
        ln -s $BIN_DIRECTORY/../config/_htaccess $ORIG_BUILDDIR/../.htaccess
    fi

    # Recreate "stable" link if needed
    STABLE_VERSION=$(find $ORIG_BUILDDIR/.. -maxdepth 1 -type d -exec basename {} \; \
        | grep -E "^[0-9]+\." | sort -rV | head -n1)
    if [ ! -r "$ORIG_BUILDDIR/../$STABLE_VERSION/objects.inv" ]; then
        # Highest version is not a Sphinx project => bad output thus skip!
        STABLE_VERSION=""
    fi
    if [ -z "$STABLE_VERSION" ] && [ "$VERSION" == "latest" ]; then
        STABLE_VERSION=latest
    fi
    if [ -n "$STABLE_VERSION" ]; then
        if [ ! -r "$ORIG_BUILDDIR/../stable" ] || [ -h "$ORIG_BUILDDIR/../stable" ]; then
            pushd $ORIG_BUILDDIR/.. >/dev/null
            echo "Recreating stable symbolic link in $PWD"
            rm -I stable
            ln -s $STABLE_VERSION stable
            popd >/dev/null
        fi
    fi

    BUILDDIR=$BACKUP_BUILDDIR
}

# ------------------------------------------------------
# MAIN SCRIPT
# ------------------------------------------------------
if [ -r "REBUILD_REQUESTED" ]; then
    projectinfo2stdout

    if [ -n "$GITURL" ]; then
        if [ ! -r "$GITDIR" ]; then
            git clone $GITURL $GITDIR
        fi
        cd $GITDIR
        if [ ! -d ".git" ]; then
            echo "Cannot proceed, not a Git directory: $GITDIR" 2>&1
            exit 2
        fi
        # Discard any change
        git reset
        git checkout .
        # Retrieve changes
        git pull
        # Switch to the actual branch
        git checkout $GITBRANCH
        git status
    elif [ ! -r "$GITDIR" ]; then
        echo "No Git URL provided and non-existing directory: $GITDIR" 2>&1
        exit 3
    fi

    # Check for valid documentation
    if [ ! -r "$T3DOCDIR/Index.rst" ] && [ ! -r "$T3DOCDIR/README.rst" ]; then
        if [ -r "./README.rst" ]; then
            T3DOCDIR=$GITDIR
        else
            echo "No documentation found: $GITDIR" 2>&1
            exit 4
        fi
    fi

    rebuildneeded
    if [ $? -eq 0 ]; then
        echo "Documentation did not change: rebuild is not needed"
        # Remove request
        rm "$MAKE_DIRECTORY/REBUILD_REQUESTED"
        exit 0
    fi

    # check include files
    $BIN_DIRECTORY/check_include_files.py --verbose "$T3DOCDIR" > "${MAKE_DIRECTORY}/included-files-check.log.txt"
    if [ $? -ne 0 ]; then
        echo "Problem with include files"
        # Remove request
        rm "$MAKE_DIRECTORY/REBUILD_REQUESTED"
        exit 5
    fi

    if [ -r "$GITDIR" ]; then
        pushd $T3DOCDIR >/dev/null

        # Temporarily remove localization directories from Sphinx to prevent
        # warnings with unreferenced files and duplicate labels
        if [ -n "$GITURL" ]; then
            find . -maxdepth 1 -regex ".*/Localization\.[a-zA-Z_]*$" -exec rm -rf {} \;
        else
            find . -maxdepth 1 -regex ".*/Localization\.[a-zA-Z_]*$" -exec mv {} ../. \;
        fi

        popd >/dev/null
    fi

    BACKUP_T3DOCDIR=$T3DOCDIR
    renderdocumentation $T3DOCDIR $T3DOCDIR 0

    if [ -r "$GITDIR" ]; then
        pushd $T3DOCDIR >/dev/null

        # Fetch back localization directories
        if [ -n "$GITURL" ]; then
            git reset
            git checkout .
            git pull
            git checkout $GITBRANCH
        else
            find .. -maxdepth 1 -regex ".*/Localization\.[a-zA-Z_]*$" -exec mv {} . \;
        fi

        popd >/dev/null
    fi

    if [ "$PACKAGE_LANGUAGE" == "default" ]; then
        pushd $T3DOCDIR >/dev/null
        for PACKAGE_LANGUAGE in $(find . -maxdepth 1 -regex ".*/Localization\.[a-z][a-z]_[A-Z][A-Z]$" | $SED_EXTENDED 's/.*\.(.._..)/\1/'); do
            if [ -r "$T3DOCDIR/Localization.${PACKAGE_LANGUAGE}/Index.rst" ]; then
                renderdocumentation $T3DOCDIR $T3DOCDIR/Localization.${PACKAGE_LANGUAGE} 1
            fi
        done
        popd >/dev/null
    fi

    # Remove request
    rm REBUILD_REQUESTED
fi

cp cron_rebuild.conf dirs-of-last-build.txt
echo "----------------------------------------" >> dirs-of-last-build.txt
echo "MAKE_DIRECTORY : $MAKE_DIRECTORY" >> dirs-of-last-build.txt
echo "BUILDDIR       : $BUILDDIR"       >> dirs-of-last-build.txt
echo "T3DOCDIR       : $T3DOCDIR"       >> dirs-of-last-build.txt
echo "STABLE_VERSION : $STABLE_VERSION" >> dirs-of-last-build.txt

popd >/dev/null

