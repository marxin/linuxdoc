#!/usr/bin/env python3
# -*- coding: utf-8; mode: python -*-
# pylint: disable=C0103

u"""
    autodoc
    ~~~~~~~

    Implementation of the ``kernel-autodoc`` command.

    :copyright:  Copyright (C) 2016  Markus Heiser
    :license:    GPL Version 2, June 1991 see Linux/COPYING for details.

    The ``kernel-autodoc`` command extracts documentation from Linux kernel's
    source code comments, see ``--help``::

        $ kernel-autodoc --help

    .. note::

       The kernel-autodoc command is under construction, no stable release
       yet. The command line arguments might be changed/extended in the near
       future."""

# ------------------------------------------------------------------------------
# imports
# ------------------------------------------------------------------------------

import sys
import argparse

import six

from fspath import FSPath
from . import kernel_doc as kerneldoc
from .kernel_doc import Container


# ------------------------------------------------------------------------------
# config
# ------------------------------------------------------------------------------

MARKUP = "kernel-doc" # "reST"
MSG    = lambda msg: sys.__stderr__.write("INFO : %s\n" % msg)
ERR    = lambda msg: sys.__stderr__.write("ERROR: %s\n" % msg)
FATAL  = lambda msg: sys.__stderr__.write("FATAL: %s\n" % msg)

TEMPLATE_INDEX="""\
.. -*- coding: utf-8; mode: rst -*-

================================================================================
%(title)s
================================================================================

.. toctree::
    :maxdepth: 1

"""

epilog = u"""This implementation of uses the kernel-doc parser
from the linuxdoc extension, for detail informations read
http://return42.github.io/sphkerneldoc/books/kernel-doc-HOWTO"""

# ------------------------------------------------------------------------------
def main():
# ------------------------------------------------------------------------------

    CLI = argparse.ArgumentParser(
        description = ("Parse *kernel-doc* comments from source code")
        , epilog = epilog
        , formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    CLI.add_argument(
        "srctree"
        , help    = "Folder of source code."
        , type    = lambda x: FSPath(x).ABSPATH)

    CLI.add_argument(
        "doctree"
        , help    = "Folder to place reST documentation."
        , type    = lambda x: FSPath(x).ABSPATH)

    CLI.add_argument(
        "--sloppy"
        , action  = "store_true"
        , help    = "Sloppy comment check, reports only severe errors.")

    CLI.add_argument(
        "--force"
        , action  = "store_true"
        , help    = "Don't stop if doctree exists.")

    CLI.add_argument(
        "--markup"
        , choices = ["reST", "kernel-doc"]
        , default = "reST"
        , help    = (
            "Markup of the comments. Change this option only if you know"
            " what you do. New comments must be marked up with reST!"))

    CMD = CLI.parse_args()

    if not CMD.srctree.EXISTS:
        ERR("%s does not exists." % CMD.srctree)
        sys.exit(42)

    if not CMD.srctree.ISDIR:
        ERR("%s is not a folder." % CMD.srctree)
        sys.exit(42)

    if not CMD.force and CMD.doctree.EXISTS:
        ERR("%s is in the way, remove it first" % CMD.doctree)
        sys.exit(42)

    for fname in CMD.srctree.reMatchFind(r"^.*\.[ch]$"):
        if fname.startswith(CMD.srctree/"Documentation"):
            continue
        autodoc_file(fname, CMD)

    insert_index_files(CMD.doctree)

# ------------------------------------------------------------------------------
def autodoc_file(fname, CMD):
# ------------------------------------------------------------------------------

    fname = fname.relpath(CMD.srctree)
    opts = kerneldoc.ParseOptions(
        rel_fname       = fname
        , src_tree      = CMD.srctree
        , verbose_warn  = not (CMD.sloppy)
        , markup        = CMD.markup )

    parser = kerneldoc.Parser(opts, kerneldoc.NullTranslator())
    try:
        parser.parse()
    except Exception: # pylint: disable=W0703
        FATAL("kernel-doc markup of %s seems buggy / can't parse" % opts.fname)
        return

    if not parser.ctx.dump_storage:
        # no kernel-doc comments found
        MSG("parsed: NONE comments: %s" % opts.fname)
        return

    MSG("parsed: %4d comments: %s" % (len(parser.ctx.dump_storage), opts.fname))

    try:
        rst = six.StringIO()
        translator = kerneldoc.ReSTTranslator()
        opts.out   = rst

        # First try to output reST, this might fail, because the kernel-doc
        # parser part is to tollerant ("bad lines", "function name and function
        # declaration are different", etc ...).
        parser.parse_dump_storage(translator=translator)

        outFile = CMD.doctree / fname.replace(".","_") + ".rst"
        outFile.DIRNAME.makedirs()
        with outFile.openTextFile(mode="w") as out:
            out.write(rst.getvalue())

    except Exception: # pylint: disable=W0703
        FATAL("kernel-doc markup of %s seems buggy / can't parse" % opts.fname)
        return

# ------------------------------------------------------------------------------
def insert_index_files(folder):
# ------------------------------------------------------------------------------

    for folder, dirnames, filenames in folder.walk():
        ctx = Container( title = folder.FILENAME )
        dirnames.sort()
        filenames.sort()
        indexFile = folder / "index.rst"
        MSG("create index: %s" % indexFile)
        with indexFile.openTextFile(mode="w") as index:
            index.write(TEMPLATE_INDEX % ctx)
            for d in dirnames:
                index.write("    %s/index\n" % d.FILENAME)
            for f in filenames:
                if f.FILENAME == "index":
                    continue
                index.write("    %s\n" % f.FILENAME)
