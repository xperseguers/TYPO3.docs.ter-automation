===========================================
TYPO3 Python Doc Builder: t3pdb_sxw2html.py
===========================================

:author: Martin Bless
:email:  martin@mbless.de
:date:   2012-09-03, 2013-08-02


What does it do?
================

``t3pdb_sxw2html.py`` is an OpenOffice to ReST converter.

It reads an OpenOffice document and creates ReST files, HTML files and
a complete TYPO3 Sphinx documentation project.

How to
======

- To run this locally on your personal machine you have to install
  ((some software)): http://wiki.typo3.org/Rendering_reST

- Get T3PythonDocBuilderPackage from git://git.typo3.org/Documentation/RestTools.git

- Goto the T3PythonDocBuilder folder::

    $ cd ((...)) T3PythonDocBuilderPackage/src/T3PythonDocBuilder

- Provide the path to an OpenOffice manual::

    $ infile=~/example_manual.sxw

- Provide the path to a temp folder for temporary file storage::

    $ tempdir=~/temp

- Run the application::

    python  t3pdb_sxw2html.py   $infile $tempdir


What you should get
===================

$tempdir/t3pdb
--------------
A newly created folder containing all output. The application will
remove the complete folder 't3pdb' the next time you are running it
with the same $tempdir parameter.


$tempdir/t3pdb/*
----------------
=================  =====================================
file               description
=================  =====================================
manual.html        saved by OpenOffice as HTML
manual.dl.rst      single ReST file using "definition list" markup
manual.t3flt.rst   single ReST file using "t3-field-list-table" directive for tables
manual.flt.rst     single ReST file using "field-list-table" directive for tables (deprecated)
manual.dl.html     single HTML file renderd by Docutils from manual.dl.rst
manual.t3flt.html  single HTML file renderd by Docutils from manual.t3flt.rst
manual.flt.html    single HTML file renderd by Docutils from manual.flt.rst (deprecated)
manual-<images>    written by OpenOffice
=================  =====================================


$tempdir/t3pdb/Documentation
----------------------------

This is a complete Sphinx Documentation project in TYPO3-style!


$tempdir/t3pdb/Documentation/_make
----------------------------------

Windows:
   Click "make-html.bat" to render the Sphinx project to using the
   'typo3sphinx' theme.

Linux/Mac:
   do ``make html``


$tempdir/t3pdb/Documentation/_make/_not_versioned
-------------------------------------------------

These are logfiles of the Sphinx builder process.


$tempdir/t3pdb/logs/
--------------------

manual.t3flt.rst.t3rst2html-warnings.txt (**important**)
   Errors and warnings when parsing ReST

manual.dl.rst.t3rst2html-warnings.txt (**important**)
   Errors and warnings when parsing ReST

manual.flt.rst.t3rst2html-warnings.txt (**important**)
   Errors and warnings when parsing ReST


manual.html.tidy-error-log.txt
   Notes from tidy when it's creating xhtml from html.

manual.html.restparser-log.txt
   Notes of the restparser about what has been done.

manual.html.restparser-tree.txt
   A tree like dump of the input html.
   This is useful for debugging the HTML parser and ReST writer.


manual.dl.rst.t3rst2html-stderr-log.txt
   stderr output when doing ``python t3rst2html.py``

manual.dl.rst.t3rst2html-stdout.txt
   stdout output when doing ``python t3rst2html.py``

manual.flt.rst.t3rst2html-stderr-log.txt
   stderr output when doing ``python t3rst2html.py``

manual.t3flt.rst.t3rst2html-stderr-log.txt
   stderr output when doing ``python t3rst2html.py``

manual.flt.rst.t3rst2html-stdout.txt
   stderr output when doing ``python t3rst2html.py``

manual.t3flt.rst.t3rst2html-stdout.txt
   stderr output when doing ``python t3rst2html.py``


$tempdir/t3pdb/_sliced
----------------------
Temporary files of an intermediate step. Can be removed.



2013-08-02, new: Convert *.gif to *.png
---------------------------------------

Images of the OpenOffice document typically have names like
:file:`manual_html_11cdfe72.gif`. Since GIF files are not garanteed to
work in Latex they are now converted to PNG and saved additionally as
'GIF-file-name.gif'+'.png'. So in this case there will be and
additional file :file:`manual_html_11cdfe72.gif.png`. The references to
the images are changed in the :file:'manual.html' by a simple
"string search and replace" from ``*.gif`` to ``*.gif.png``.

The GIF files are not removed but kept as a measure of precaution. It
should be ok to remove them since they are not being referenced.

.. note::

   The `Python Imaging Library (PIL) <http://www.pythonware.com/products/pil/>`__
   is used for the GIF to PNG conversion. Available via "easy_install"
   and the `Python Package Index <https://pypi.python.org/pypi/PIL>`__.

   This is not a new requirement since its already installed on the
   TYPO3 Docs server.



((to be continued))

