'''
map_residues.py - liftover for residues
=======================================

:Author: Andreas Heger
:Release: $Id$
:Date: |today|
:Tags: Python

Purpose
-------

maps a list of residues in a master sequence based on an explicit
(multiple) alignment.

Options::

    -m, --master    number of sequence to use as master (default is first row)
    -f, --format    alignment format (plain is the default and so far the only
                    supported option)       

Usage
-----

Example::

   python map_residues.py --help

Type::

   python map_residues.py --help

for command line help.

Command line options
--------------------

'''

import sys
import re
import os
import string
import getopt
import alignlib_lite

param_master = 0
param_format = None
param_multiple_alignment = None

GAPCHARS = (".", "-")


def main(argv=None):
    """script main.

    parses command line options in sys.argv, unless *argv* is given.
    """

    if argv is None:
        argv = sys.argv

    try:
        optlist, args = getopt.getopt(sys.argv[1:],
                                      "V:m:f:h",
                                      ["Verbose=", "master=",
                                       "format=", "help", "version"])

    except getopt.error, msg:
        print globals()["__doc__"], msg
        sys.exit(2)

    for o, a in optlist:
        if o in ("-h", "--help"):
            print globals()["__doc__"]
            sys.exit(0)
        elif o in ("--version", ):
            print "version="
            sys.exit(0)
        elif o in ("-f", "--format"):
            param_format = a
        elif o in ("-m", "--master"):
            param_master = string.atoi(a)

    if len(args) != 1:
        print "please specify a multiple alignment."
        print globals()["__doc__"]
        sys.exit(1)

    lines = map(lambda x: string.split(
        x[:-1], "\t"), open(args[0], "r").readlines())

    residues = filter(lambda x: not re.match("#", x), sys.stdin.readlines())

    if len(lines) <= param_master:
        print "master alignment does no exist in the alignment."
        print globals()["__doc__"]
        sys.exit(1)

    master_from, master_ali, master_to, master_id = lines[param_master]

    print "# master=", master_id

    for index in range(len(lines)):
        if param_master == index:
            continue

        sbjct_from, sbjct_ali, sbjct_to, sbjct_id = lines[index]

        print "#", sbjct_id
        map_master2sbjct = alignlib_lite.py_makeAlignataVector()

        sbjct_index = string.atoi(sbjct_from)
        master_index = string.atoi(master_from)

        map_sbjct2residue = {}

        for x in range(len(master_ali)):

            if master_ali[x] not in GAPCHARS and sbjct_ali[x] not in GAPCHARS:
                map_master2sbjct.addPairExplicit(master_index, sbjct_index, 0)
                map_sbjct2residue[sbjct_index] = sbjct_ali[x]

            if master_ali[x] not in GAPCHARS:
                master_index += 1

            if sbjct_ali[x] not in GAPCHARS:
                sbjct_index += 1

        for line in residues:
            r = string.atoi(string.split(line[:-1], "\t")[0])
            sbjct_index = map_master2sbjct.mapRowToCol(r)
            if sbjct_index:
                print string.join((str(sbjct_index), map_sbjct2residue[sbjct_index]), "\t") + "\t" + line[:-1]
            else:
                print string.join(("0", "X"), "\t") + "\t" + line[:-1]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
