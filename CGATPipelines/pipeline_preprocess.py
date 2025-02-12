

##########################################################################
#
#   MRC FGU Computational Genomics Group
#
#   $Id$
#
#   Copyright (C) 2009 Tildon Grant Belgard
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
##########################################################################

"""
====================
Pre-process pipeline
====================

:Author: CGAT (various)
:Release: $Id$
:Date: |today|
:Tags: Python

(See the readqc pipeline for details of the readqc functions (target ``readqc``).)

The purpose of this pipeline is to pre-process reads (target ``full``). 

Implemented tasks are:

   * :meth:`removeContaminants` - remove contaminants from read sets
   * :meth:`trim` - trim reads by a certain amount
   * :meth:`filter` - filter reads by quality score
   * :meth:`sample` - sample a certain proportion of reads

Individual tasks are enabled in the configuration file.

Usage
=====

See :ref:`PipelineSettingUp` and :ref:`PipelineRunning` on general information how to use CGAT pipelines.

Configuration
-------------

No general configuration required.

Removing contaminants
---------------------

Use the task :meth:`removeContaminants` to remove contaminants from read
sets.

Contaminant sequences are listed in the file :file:`contaminants.fasta`. 
If not given, a file with standard Illumina adapators will be created 
to remove adaptor contamination.

The task will create output files called :file:`nocontaminants-<infile>`.

The pipeline can then be re-run in order to add stats on the contaminant-removed
files.

.. note::

   Colour space filtering has not been implemented yet.

Input
-----

Reads are imported by placing files or linking to files in the :term:`working directory`.

The default file format assumes the following convention:

   <sample>-<condition>-<replicate>.<suffix>

``sample`` and ``condition`` make up an :term:`experiment`, while ``replicate`` denotes
the :term:`replicate` within an :term:`experiment`. The ``suffix`` determines the file type.
The following suffixes/file types are possible:

sra
   Short-Read Archive format. Reads will be extracted using the :file:`fastq-dump` tool.

fastq.gz
   Single-end reads in fastq format.

fastq.1.gz, fastq2.2.gz
   Paired-end reads in fastq format. The two fastq files must be sorted by read-pair.

.. note::

   Quality scores need to be of the same scale for all input files. Thus it might be
   difficult to mix different formats.

Requirements
------------

On top of the default CGAT setup, the pipeline requires the following software to be in the 
path:

+--------------------+-------------------+------------------------------------------------+
|*Program*           |*Version*          |*Purpose*                                       |
+--------------------+-------------------+------------------------------------------------+
|fastqc              |>=0.9.0            |read quality control                            |
+--------------------+-------------------+------------------------------------------------+
|sra-tools           |                   |extracting reads from .sra files                |
+--------------------+-------------------+------------------------------------------------+
|picard              |>=1.38             |bam/sam files. The .jar files need to be in your|
|                    |                   | CLASSPATH environment variable.                |
+--------------------+-------------------+------------------------------------------------+

Pipeline output
===============

The major output is a set of HTML pages and plots reporting on the quality of the sequence archive

Example
=======

Example data is available at http://www.cgat.org/~andreas/sample_data/pipeline_readqc.tgz.
To run the example, simply unpack and untar::

   wget http://www.cgat.org/~andreas/sample_data/pipeline_readqc.tgz
   tar -xvzf pipeline_readqc.tgz
   cd pipeline_readqc
   python <srcdir>/pipeline_readqc.py make full


TODO
====

Code needs to be modularised, adapter sequences need to be moved to /ifs/annotation.

Code
====

"""

###################################################
###################################################
###################################################
# load modules
###################################################

# import ruffus
from ruffus import *

# import useful standard python modules
import sys
import os
import re
import shutil
import itertools
import math
import glob
import time
import gzip
import collections
import random
import cStringIO

import CGAT.Experiment as E
import logging as L
import CGAT.Database as Database
import sys
import os
import re
import shutil
import string
import itertools
import math
import glob
import time
import gzip
import collections
import random
import numpy
import sqlite3
import CGAT.GTF as GTF
import CGAT.IOTools as IOTools
import CGAT.IndexedFasta as IndexedFasta
import CGAT.FastaIterator as FastaIterator
import CGAT.Tophat as Tophat
import rpy2.robjects as ro
import CGATPipelines.PipelineGeneset as PipelineGeneset
import CGATPipelines.PipelineMapping as PipelineMapping
import CGAT.Stats as Stats
import CGATPipelines.PipelineTracks as PipelineTracks
import CGAT.Pipeline as P
import CGAT.Fastq as Fastq
import CGAT.CSV2DB as CSV2DB

###################################################
###################################################
###################################################
# Pipeline configuration
###################################################

# load options from the config file
P.getParameters(
    ["%s/pipeline.ini" % os.path.splitext(__file__)[0],
     "../pipeline.ini",
     "pipeline.ini"])
PARAMS = P.PARAMS

#########################################################################
#########################################################################
#########################################################################
# define input files
INPUT_FORMATS = ("*.fastq.1.gz", "*.fastq.gz", "*.sra", "*.csfasta.gz")
REGEX_FORMATS = regex(r"(\S+).(fastq.1.gz|fastq.gz|sra|csfasta.gz)")

#########################################################################
#########################################################################
#########################################################################


@follows(mkdir(PARAMS["exportdir"]), mkdir(os.path.join(PARAMS["exportdir"], "fastqc")))
@transform(INPUT_FORMATS,
           REGEX_FORMATS,
           r"\1.fastqc")
def runFastqc(infiles, outfile):
    '''convert sra files to fastq and check mapping qualities are in solexa format. 
    Perform quality control checks on reads from .fastq files.'''
    to_cluster = True
    m = PipelineMapping.FastQc(nogroup=PARAMS["readqc_no_group"])
    statement = m.build((infiles,), outfile)
    P.run()

#########################################################################
#########################################################################
#########################################################################
##
#########################################################################


def FastqcSectionIterator(infile):
    data = []
    for line in infile:
        if line.startswith(">>END_MODULE"):
            yield name, status, header, data
        elif line.startswith(">>"):
            name, status = line[2:-1].split("\t")
            data = []
        elif line.startswith("#"):
            header = "\t".join([x for x in line[1:-1].split("\t") if x != ""])
        else:
            data.append(
                "\t".join([x for x in line[:-1].split("\t") if x != ""]))


@jobs_limit(1, "db")
@transform(runFastqc, suffix(".fastqc"), "_fastqc.load")
def loadFastqc(infile, outfile):
    '''load FASTQC stats.'''

    track = P.snip(infile, ".fastqc")

    filename = os.path.join(
        PARAMS["exportdir"], "fastqc", track + "*_fastqc", "fastqc_data.txt")

    for fn in glob.glob(filename):
        prefix = os.path.basename(os.path.dirname(fn))
        results = []

        for name, status, header, data in FastqcSectionIterator(IOTools.openFile(fn)):
            # do not collect basic stats, see loadFastQCSummary
            if name == "Basic Statistics":
                continue

            parser = CSV2DB.buildParser()
            (options, args) = parser.parse_args([])
            options.tablename = prefix + "_" + re.sub(" ", "_", name)
            options.allow_empty = True

            inf = cStringIO.StringIO("\n".join([header] + data) + "\n")
            CSV2DB.run(inf, options)
            results.append((name, status))

        # load status table
        parser = CSV2DB.buildParser()
        (options, args) = parser.parse_args([])
        options.tablename = prefix + "_status"
        options.allow_empty = True

        inf = cStringIO.StringIO(
            "\n".join(["name\tstatus"] + ["\t".join(x) for x in results]) + "\n")
        CSV2DB.run(inf, options)

    P.touch(outfile)


def collectFastQCSections(infiles, section):
    '''iterate over all fastqc files and extract a particular section.'''
    results = []

    for infile in infiles:

        track = P.snip(infile, ".fastqc")

        filename = os.path.join(
            PARAMS["exportdir"], "fastqc", track + "*_fastqc", "fastqc_data.txt")

        for fn in glob.glob(filename):
            prefix = os.path.basename(os.path.dirname(fn))
            for name, status, header, data in FastqcSectionIterator(IOTools.openFile(fn)):
                if name == section:
                    results.append((track, status, header, data))

    return results


@merge(runFastqc, "status_summary.tsv.gz")
def buildFastQCSummaryStatus(infiles, outfile):
    '''load fastqc status summaries into a single table.'''

    outf = IOTools.openFile(outfile, "w")
    first = True
    for infile in infiles:
        track = P.snip(infile, ".fastqc")
        filename = os.path.join(
            PARAMS["exportdir"], "fastqc", track + "*_fastqc", "fastqc_data.txt")

        for fn in glob.glob(filename):
            prefix = os.path.basename(os.path.dirname(fn))
            results = []

            names, stats = [], []
            for name, status, header, data in FastqcSectionIterator(IOTools.openFile(fn)):
                stats.append(status)
                names.append(name)

            if first:
                outf.write("track\tfilename\t%s\n" % "\t".join(names))
                first = False

            outf.write("%s\t%s\t%s\n" %
                       (track, os.path.dirname(fn), "\t".join(stats)))
    outf.close()


@merge(runFastqc, "basic_statistics_summary.tsv.gz")
def buildFastQCSummaryBasicStatistics(infiles, outfile):
    '''load fastqc summaries into a single table.'''

    data = collectFastQCSections(infiles, "Basic Statistics")

    outf = IOTools.openFile(outfile, "w")
    first = True
    for track, status, header, rows in data:
        rows = [x.split("\t") for x in rows]
        if first:
            headers = [row[0] for row in rows]
            outf.write("track\t%s\n" % "\t".join(headers))
            first = False
        outf.write("%s\t%s\n" % (track, "\t".join([row[1] for row in rows])))
    outf.close()


@transform((buildFastQCSummaryStatus, buildFastQCSummaryBasicStatistics),
           suffix(".tsv.gz"), ".load")
def loadFastqcSummary(infile, outfile):
    P.load(infile, outfile, options="--index=track")

#########################################################################
#########################################################################
#########################################################################
# adaptor trimming
#########################################################################
# these are the adaptors and PCR primers for used in various illumina libarary preps
# see https://cgatwiki.anat.ox.ac.uk/xwiki/bin/view/CGAT/Illumina+Sequencing#HIlluminaAdaptors.html
# currently included are primers/adaptors from:
# TruSeq DNA HT and RNA HT Sample Prep Kits; TruSeq DNA v1/v2/LT RNA v1/v2/LT and ChIP Sample Prep Kits;
# Oligonucleotide Sequences for TruSeq Small RNA Sample Prep Kits; Oligonucleotide Sequences for Genomic DNA;
# Oligonucleotide Sequences for the v1 and v1.5 Small RNA Sample Prep Kits;
# Paired End DNA Oligonucleotide Sequences; Script Seq Adaptors;
# Oligonucleotide Sequences for the Multiplexing Sample Prep Oligo Only Kits.
ILLUMINA_ADAPTORS = {"Genomic-DNA-Adaptor": "GATCGGAAGAGCTCGTATGCCGTCTTCTGCTTG",
                     "Genomic/Paired-End/Oligo-Only-Adaptor": "ACACTCTTTCCCTACACGACGCTCTTCCGATCT",
                     "Genomic/TruSeq-Universal/PE/OO/ScriptSeq-Adaptor/PCR-Primer": "AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT",
                     "Genomic-PCR-Primer": "CAAGCAGAAGACGGCATACGAGCTCTTCCGATCT",
                     "Paired-End-Adaptor": "GATCGGAAGAGCGGTTCAGCAGGAATGCCGAG",
                     "Paired-End-PCR-Primer": "CAAGCAGAAGACGGCATACGAGATCGGTCTCGGCATTCCTGCTGAACCGCTCTTCCGATCT",
                     "TruSeq-HT-Adaptor-I3": "GATCGGAAGAGCACACGTCTGAACTCCAGTCACTTAGGCATCTCGTATGC",
                     "TruSeq-Adaptor-I7": "GATCGGAAGAGCACACGTCTGAACTCCAGTCACCAGGTTCTATCTCGTAT",
                     "TruSeq-Adaptor-I4": "GATCGGAAGAGCACACGTCTGAACTCCAGTCACTGCCGGCTATCTCGTAT",
                     "TruSeq-HT-Adaptor-I5": "AATGATACGGCGACCACCGAGATCTACACNNNNNACACTCTTTCCCTACACGACGCTCTTCCGATCT",
                     "TruSeq-HT-Adaptor-I7": "GATCGGAAGAGCACACGTCTGAACTCCAGTCACNNNNNNNATCTCGTATGCCGTCTTCTGCTTG",
                     "TruSeq-LT-Adaptor-I6": "GATCGGAAGAGCACACGTCTGAACTCCAGTCACNNNNNNATCTCGTATGCCGTCTTCTGCTTG",
                     "TruSeq-Adaptor-I11": "GATCGGAAGAGCACACGTCTGAACTCCAGTCACGGCTACATCTCGTATGC",
                     "TruSeq-Small-RNA-Adaptor": "TGGAATTCTCGGGTGCCAAGG",
                     "TruSeq-Small-RNA-RT-Primer": "GCCTTGGCACCCGAGAATTCCA",
                     "TruSeq-Small-RNA-PCR-Primer": "AATGATACGGCGACCACCGAGATCTACACGTTCAGAGTTCTACAGTCCGA",
                     "TruSeq-Small-RNA-PCR-Primer-I6": "CAAGCAGAAGACGGCATACGAGATNNNNNNGTGACTGGAGTTCCTTGGCACCCGAGAATTCCA",
                     "Oligo-Only-Adaptor": "GATCGGAAGAGCACACGTCT",
                     "Oligo-Only-PCR-Primer": "GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT",
                     "Oligo-Only-PCR-Primer-I7": "CAAGCAGAAGACGGCATACGAGATNNNNNNNTGACTGGAGTTC",
                     "Small-RNA-v1-RT-Primer": "CAAGCAGAAGACGGCATACGA",
                     "Small-RNA-PCR-Primer": "AATGATACGGCGACCACCGACAGGTTCAGAGTTCTACAGTCCGA",
                     "ScriptSeq-Adaptor-I6": "CAAGCAGAAGACGGCATACGAGATNNNNNNGTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT",
                     "Exo_WTCHG_V.1_IlluminaWTCHGPrimer1": "AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT",
                     "Exo_WTCHG_V.1_WTCHGIndex1": "CAAGCAGAAGACGGCATACGAGATAGTTAACAGTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT",
                     "Exo_WTCHG_V.1_ChIP_exo_Adapt1": "AGATCGGAAGA",
                     "Exo_WTCHG_V.1_ChIP_exo_Adapt1.1": "TCCCTACACGACGCTCTTCCGATCT",
                     "Exo_WTCHG_V.1_ExtPr1": "CCTACACGACGCTCTTCCGATCT",
                     "Exo_WTCHG_V.1_ChIP_exo_Adapt2": "GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT",
                     "Exo_WTCHG_V.1_ChIP_exo_Adapt2.1": "AGATCGGAAGAGCACACGTCTGAACTCCAGTC",
                     "Exo_WTCHG_V.2_IlluminaWTCHGPrimer1": "AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT",
                     "Exo_WTCHG_V.2_WTCHGIndex1": "CAAGCAGAAGACGGCATACGAGATAGTTAACAGTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT",
                     "Exo_WTCHG_V.2_ChIP_exo_Adapt1": "GATCGGAAGAGCGTCGTGTAGGGA",
                     "Exo_WTCHG_V.2_ChIP_exo_Adapt1.1": "TCCCTACACGACGCTCTTCCGATCT",
                     "Exo_WTCHG_V.2_ExtPr1": "CCTACACGACGCTCTTCCGATCT",
                     "Exo_WTCHG_V.2_ChIP_exo_Adapt2": "GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT",
                     "Exo_WTCHG_V.2_ChIP_exo_Adapt2.1": "GATCGGAAGAGCACACGTCTGAACTCCAGTC",
                     "SmartIIA": "AAGCAGTGGTATCAACGCAGAGTAC",
                     "Illumina-Nextera-v2-Primer1": "GTCTCGTGGGCTCGGAGATGTGTATAAGAGACAG",
                     "Illumina-Nextera-v2-Primer2": "TCGTCGGCAGCGTCAGATGTGTATAAGAGACAG",
                     "Illumina-Paired-End_Primer2": "CGGTTCAGCAGGAATGCCGAGACCGATCTCGTATGCCGTCTTCTGCTTGA",
                     "Illumina-Single-End-Adpator2": "GATCGGAAGAGCTCGTATGCCGTCTTCTGCTTGGAAAGGAAGAGCACACG",
                     "Nextera-Transposon-End-Sequence": "AGATGTGTATAAGAGACAG",
                     "Epicentre-Nextera-Primer1": "AATGATACGGCGACCACCGA",
                     "Epicentre-Nextera-Primer2": "CAAGCAGAAGACGGCATACGA",
                     "Epicentre-Nextera-Read1": "GCCTCCCTCGCGCCATC",
                     "Epicentre-Nextera-Read2": "GCCTTGCCAGCCCGCTC",
                     "NETseq-linker-1": "CTGTAGGCACCATCAAT",
                     "NETseq-RT-primer_5prime": "ATCTCGTATGCCGTCTTCTGCTTG",
                     "NETseq-RT-primer_3prime": "TCCGACGATCATTGATGGTGCCTACAG",
                     "NETseq-PCR-primer-oLSC008-bc1": "AATGATACGGCGACCACCGAGATCTACACGATCGGAAGAGCACACGTCTGAACTCCAGTCACATGCCATCCGACGATCATTGATGG"
                     }

#########################################################################
#########################################################################
#########################################################################


@merge(None, "contaminants.fasta")
def outputContaminants(infile, outfile):
    '''output file with contaminants.
    if contamination_reverse_complement is selected, then the reverse
    complement of each sequence is also written to the outfile. 
    '''
    outf = IOTools.openFile(outfile, "w")
    for key, value in ILLUMINA_ADAPTORS.iteritems():
        outf.write(">%s\n%s\n" % (key, value))
        if PARAMS["contamination_reverse_complement"]:
            key_rc = key + "_rc"
            value_rc = value[::-1]
            value_rc = value_rc.translate(string.maketrans("ACTGN", "TGACN"))
            outf.write(">%s\n%s\n" % (key_rc, value_rc))
        else:
            continue
    outf.close()


def listAdaptors(infile):
    adaptors = []
    for entry in FastaIterator.FastaIterator(IOTools.openFile(infile)):
        adaptors.append(
            "%s %s" % (PARAMS["contamination_trim_type"], entry.sequence))
    adaptors = " ".join(adaptors)

    return adaptors

#########################################################################
#########################################################################
#########################################################################


@transform([x for x in
            glob.glob("*.fastq.gz") + glob.glob("*.fastq.1.gz") +
            glob.glob("*.fastq.2.gz")
            if not x.startswith("nocontaminants")],
           regex(r"(\S+).(fastq.1.gz|fastq.gz|fastq.2.gz|csfasta.gz)"),
           add_inputs(outputContaminants),
           r"nocontaminants.\1.\2")
def removeContaminants(infiles, outfile):
    '''remove adaptor contamination from fastq files.

    This method uses cutadapt.
    '''

    infile, contaminant_file = infiles

    adaptors = []
    for entry in FastaIterator.FastaIterator(IOTools.openFile(contaminant_file)):
        adaptors.append("-a %s" % entry.sequence)

    adaptors = " ".join(adaptors)
    to_cluster = True

    statement = '''
    cutadapt 
    %(adaptors)s
    --overlap=%(contamination_min_overlap_length)i
    --format=fastq
    %(contamination_options)s
    <( zcat < %(infile)s )
    2> %(outfile)s.log
    | gzip > %(outfile)s
    '''
    P.run()

#########################################################################
#########################################################################
#########################################################################


def checkPairs(infile):
    '''check for paired read files'''
    if infile.endswith(".fastq.1.gz"):
        infile2 = P.snip(infile, ".fastq.1.gz") + ".fastq.2.gz"
        assert os.path.exists(
            infile2), "second part of read pair (%s) missing" % infile2
    else:
        infile2 = None

    return infile2

#########################################################################
#########################################################################
#########################################################################


@transform([x for x in
            glob.glob("*.fastq.gz") + glob.glob("*.fastq.1.gz")
            if not x.startswith("processed.")],
           regex(r"(\S+).(fastq.1.gz|fastq.gz|csfasta.gz)"),
           add_inputs(outputContaminants),
           r"processed.\1.\2")
def processReads(infiles, outfile):
    '''process reads.'''

    infile, contaminant_file = infiles

    do_sth = False
    to_cluster = True

    infile2 = checkPairs(infile)

    if infile2:
        track = P.snip(outfile, ".fastq.1.gz")
        outfile2 = P.snip(outfile, ".fastq.1.gz") + ".fastq.2.gz"
    else:
        track = P.snip(outfile, ".fastq.gz")

    if PARAMS["process_combine_reads"]:
        E.warn(
            "combining reads cannot be can not be combined with other processing for paired ended reads")
        if not infile2:
            raise IOError("must have paired data to combine reads")

        read_len, frag_len, frag_stdev = PARAMS["combine_reads_read_length"], \
            PARAMS["combine_reads_fragment_length"], \
            PARAMS["combine_reads_fragment_length_stdev"]

        fragment_options = " ".join(map(str, [read_len, frag_len, frag_stdev]))

        if PARAMS["combine_reads_max_overlap"]:
            E.warn(
                "if specifying --max-overlap read and fragment length options will be ignored")
            max_overlap = "--max-overlap=%i" % PARAMS[
                "combine_reads_max_overlap"]
            fragment_options = ""

        elif not PARAMS["combine_reads_max_overlap"] and len(fragment_options.strip().split(" ")) < 3:
            E.warn(
                "have not specified --read-len, --frag-len, --frag-len-stddev: default --max-overlap used")
            max_overlap = ""
            fragment_options = ""

        elif PARAMS["combine_reads_read_length"] and PARAMS["combine_reads_fragment_length"] and PARAMS["combine_reads_fragment_length_stdev"]:
            if PARAMS["combine_reads_max_overlap"]:
                E.warn(
                    "--max-overlap will override the specified read and fragment length options")
            max_overlap = ""
            fragment_options = """--read-len=%(read_len)i
                                  --fragment-len=%(frag_len)i
                                  --fragment-len-stddev=%(frag_stdev)i""" % locals()
        else:
            max_overlap = ""
            fragment_options = ""

        if not PARAMS["combine_reads_min_overlap"]:
            min_overlap = ""
        else:
            min_overlap = "--min-overlap=%i" % PARAMS[
                "combine_reads_min_overlap"]
        if not PARAMS["combine_reads_threads"]:
            threads = ""
        else:
            threads = "--threads=%i" % PARAMS["combine_reads_threads"]
        if not PARAMS["combine_reads_phred_offset"]:
            phred_offset = ""
        else:
            phred_offset = "--phred-offset=%i" % PARAMS[
                "combine_reads_phred_offset"]
        if not PARAMS["combine_reads_max_mismatch_density"]:
            max_mismatch_density = ""
        else:
            max_mismatch_density = "--max-mismatch-density=%f" % PARAMS[
                "combine_reads_max_mismatch_density"]

        statement = '''flash 
                     %(min_overlap)s
                     %(max_overlap)s
                     %(max_mismatch_density)s
                     %(phred_offset)s
                     %(fragment_options)s
                     --output-prefix=%(track)s
                     %(threads)s
                     --compress
                     %(infile)s %(infile2)s >> %(outfile)s.log
                     '''
        P.run()
        if PARAMS["combine_reads_concatenate"]:
            infiles = " ".join(
                [track + x for x in [".notCombined_1.fastq.gz", ".notCombined_2.fastq.gz", ".extendedFrags.fastq.gz"]])
            statement = '''zcat %(infiles)s | gzip > %(outfile)s; rm -rf %(infiles)s'''
        else:
            statement = '''mv %(track)s.extendedFrags.fastq.gz %(outfile)s'''
        P.run()
        return

    if PARAMS["process_sample"] and infile2:
        E.warn(
            "sampling can not be combined with other processing for paired ended reads")
        statement = '''zcat %(infile)s
        | python %(scriptsdir)s/fastq2fastq.py 
                                   --sample=%(sample_proportion)f 
                                   --pair=%(infile2)s 
                                   --outfile-pair=%(outfile2)s 
                                   --log=%(outfile)s_sample.log
        | gzip 
        > %(outfile)s
        '''

        P.run()
        return

    # fastx does not like quality scores below 64 (Illumina 1.3 format)
    # need to detect the scores and convert
    format = Fastq.guessFormat(IOTools.openFile(infile), raises=False)
    E.info("%s: format guess: %s" % (infile, format))
    offset = Fastq.getOffset(format, raises=False)

    if PARAMS["process_remove_contaminants"]:
        adaptors = listAdaptors(contaminant_file)
#              %(contamination_trim_type)s
        s = [ '''
        cutadapt 
              %(adaptors)s
              --overlap=%(contamination_min_overlap_length)i
              --format=fastq
              %(contamination_options)s
              <( zcat < %(infile)s )
              2>> %(outfile)s_contaminants.log
        ''' ]
        do_sth = True
    else:
        s = ['zcat %(infile)s']

    if PARAMS["process_artifacts"]:
        s.append(
            'fastx_artifacts_filter -Q %(offset)i -v %(artifacts_options)s 2>> %(outfile)s_artifacts.log')
        do_sth = True

    if PARAMS["process_trim"]:
        s.append(
            'fastx_trimmer -Q %(offset)i -v %(trim_options)s 2>> %(outfile)s_trim.log')
        do_sth = True

    # NICK - may replace fastx trimmer
    if PARAMS["process_trim_quality"]:
        s.append(
            'fastq_quality_trimmer -Q %(offset)i  -v %(trim_quality_options)s 2>> %(outfile)s_trim.log')
        do_sth = True

    if PARAMS["process_filter"]:
        s.append(
            'fastq_quality_filter -Q %(offset)i -v %(filter_options)s 2>> %(outfile)s_filter.log')
        do_sth = True

    if PARAMS["process_trimmomatic"]:
        s.append(
            'trimmomatic %(trimmomatic_datatype)s -phred%(offset)i /dev/stdin /dev/stdout %(trimmomatic_options)s')
        do_sth = True

    if PARAMS["process_sample"]:
        s.append(
            'python %(scriptsdir)s/fastq2fastq.py --sample=%(sample_proportion)f --log=%(outfile)s_sample.log')

    if not do_sth:
        E.warn("no filtering specified for %s - nothing done" % infile)
        return

    s.append("gzip")
    if not infile2:
        statement = " | ".join(s) + " > %(outfile)s"
        P.run()
    else:
        tmpfile = P.getTempFilename(".")
        tmpfile1 = tmpfile + ".fastq.1.gz"
        tmpfile2 = tmpfile + ".fastq.2.gz"

        E.warn("processing first of pair")
        # first read pair
        statement = " | ".join(s) + " > %(tmpfile1)s"
        P.run()

        # second read pair
        E.warn("processing second of pair")
        infile = infile2
        statement = " | ".join(s) + " > %(tmpfile2)s"
        P.run()

        # reconcile
        E.info("starting reconciliation")
        statement = """python %(scriptsdir)s/fastqs2fastqs.py
                           --method=reconcile
                           --output-pattern=%(track)s.fastq.%%s.gz
                           %(tmpfile1)s %(tmpfile2)s
                     > %(outfile)s_reconcile.log"""

        P.run()

        os.unlink(tmpfile1)
        os.unlink(tmpfile2)
        os.unlink(tmpfile)

##################################################################
##################################################################
##################################################################


def parseCutadapt(lines):
    '''parse cutadapt output.

    Multiple cutadapt outputs are joined.
    '''

    def _chunker(inf):
        chunk = []
        for line in inf:
            if line.startswith("==="):
                if chunk:
                    yield chunk
                chunk = []
            chunk.append(line)

    assert lines[0].startswith("cutadapt")
    results = {}

    del lines[0]
    for x, line in enumerate(lines):
        if not line.strip():
            continue
        if ":" in line:
            if line.strip().startswith("Command"):
                continue
            param, value = line[:-1].split(":")
            param = re.sub(" ", "_", param.strip()).lower()
            value = re.sub("[a-zA-Z ].*", "", value.strip())
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except:
                    pass
            results[param] = value
        else:
            break

    del lines[:x]
    results["unchanged_reads"] = int(
        results["processed_reads"]) - int(results["trimmed_reads"])
    headers = results.keys()

    adapters = {}
    for chunk in _chunker(lines):
        adapter = re.search("=== (.*) ===", chunk[0]).groups()[0]
        length, removed = re.search(
            "Adapter '.*', length (\d+), was trimmed (\d+) times", chunk[2]).groups()

        adapters[adapter] = length, removed

    return results, adapters

##################################################################
##################################################################
##################################################################


@transform(processReads,
           suffix(""),
           ".tsv")
def summarizeProcessing(infile, outfile):
    '''build processing summary.'''

    def _parseLog(inf, step):

        inputs, outputs = [], []
        if step == "reconcile":
            for line in inf:
                x = re.search(
                    "first pair: (\d+) reads, second pair: (\d+) reads, shared: (\d+) reads", line)
                if x:
                    i1, i2, o = map(int, x.groups())
                    inputs = [i1, i2]
                    outputs = [o, o]
                    break
        elif step == "contaminants":
            lines = inf.readlines()
            assert lines[0].startswith("cutadapt")
            lines = "@@@".join(lines)
            for part in lines.split("cutadapt")[1:]:
                results, adapters = parseCutadapt(
                    ("cutadapt" + part).split("@@@"))
                inputs.append(results["processed_reads"])
                outputs.append(results["unchanged_reads"])
        else:
            for line in inf:
                if line.startswith("Input:"):
                    inputs.append(
                        int(re.match("Input: (\d+) reads.", line).groups()[0]))
                elif line.startswith("Output:"):
                    outputs.append(
                        int(re.match("Output: (\d+) reads.", line).groups()[0]))

        return zip(inputs, outputs)

    infile2 = checkPairs(infile)
    if infile2:
        track = P.snip(infile, ".fastq.1.gz")
    else:
        track = P.snip(infile, ".fastq.gz")

    outf = IOTools.openFile(outfile, "w")
    outf.write("track\tstep\tpair\tinput\toutput\n")

    for step in "contaminants", "artifacts", "trim", "filter", "reconcile":
        fn = infile + "_%s.log" % step
        if not os.path.exists(fn):
            continue
        for x, v in enumerate(_parseLog(IOTools.openFile(fn), step)):
            outf.write("%s\t%s\t%i\t%i\t%i\n" % (track, step, x, v[0], v[1]))

    outf.close()

#########################################################################
#########################################################################
#########################################################################


@jobs_limit(1, "db")
@transform(summarizeProcessing,
           regex(r"processed.(\S+).fastq.*.gz.tsv"),
           r"\1_processed.load")
def loadProcessingSummary(infile, outfile):
    '''load filtering summary.'''
    P.load(infile, outfile)

#########################################################################
#########################################################################
#########################################################################


@merge(summarizeProcessing, "processing_summary.tsv")
def summarizeAllProcessing(infiles, outfile):
    '''summarize processing information.'''

    outf = IOTools.openFile(outfile, "w")
    data = []
    for infile in infiles:
        inf = IOTools.openFile(infile)
        for line in inf:
            track, step, pair, ninput, noutput = line[:-1].split("\t")
            if track == "track":
                continue
            data.append((track, step, pair, ninput, noutput))

    # sort by track, pair, input
    data.sort(key=lambda x: (x[0], x[2], -int(x[3])))
    first = True
    for key, v in itertools.groupby(data, lambda x: (x[0], x[2])):
        vals = list(v)
        track, pair = key
        ninput = int(vals[0][3])
        outputs = [int(x[4]) for x in vals]
        if first:
            outf.write("track\tpair\tninput\t%s\t%s\t%s\t%s\n" % ("\t".join([x[1] for x in vals]),
                                                                  "noutput",
                                                                  "\t".join(
                                                                      ["percent_%s" % x[1] for x in vals]),
                                                                  "percent_output"))
            first = False
        outf.write("%s\t%s\t%i\t%s\t%i\t%s\t%s\n" % (track, pair, ninput,
                                                     "\t".join(
                                                         map(str, outputs)),
                                                     outputs[-1],
                                                     "\t".join(
                                                         ["%5.2f" % (100.0 * x / ninput) for x in outputs]),
                                                     "%5.2f" % (100.0 * outputs[-1] / ninput)))
    outf.close()

#########################################################################
#########################################################################
#########################################################################


@jobs_limit(1, "db")
@transform(summarizeAllProcessing, suffix(".tsv"), ".load")
def loadAllProcessingSummary(infile, outfile):
    P.load(infile, outfile)

#########################################################################
#########################################################################
#########################################################################


@merge(removeContaminants, "filtering.summary.tsv.gz")
def summarizeFiltering(infiles, outfile):
    '''collect summary output from filtering stage.'''

    tracks = {}
    adapters = {}

    for f in infiles:
        track = f[len("nocontaminants."):]
        track = re.sub("[.].*", "", track)
        result, adapter = parseCutadapt(IOTools.openFile(f + ".log"))
        tracks[track] = result
        adapters[track] = adapter
        header = result.keys()

    outf = IOTools.openFile(outfile, "w")
    outf.write("track\t%s\n" % "\t".join(headers))

    for track, results in tracks.iteritems():
        outf.write("%s\t%s\n" %
                   (track, "\t".join(str(results[x]) for x in headers)))
    outf.close()

#########################################################################
#########################################################################
#########################################################################


@jobs_limit(1, "db")
@transform(summarizeFiltering,
           suffix(".summary.tsv.gz"),
           "_summary.load")
def loadFilteringSummary(infile, outfile):
    '''load filtering summary.'''
    P.load(infile, outfile)

#########################################################################
#########################################################################
#########################################################################


@transform([x for x in glob.glob("*.fastq.gz") + glob.glob("*.fastq.1.gz") + glob.glob("*.fastq.2.gz")], regex(r"(\S+).(fastq.1.gz|fastq.gz|fastq.2.gz|csfasta.gz)"), r"trim.\1.\2")
def trimReads(infile, outfile):
    '''trim reads to desired length using fastx

    '''

    E.warn("deprecated - use processReads instead")

    to_cluster = True
    statement = '''zcat %(infile)s | fastx_trimmer %(trim_options)s 2> %(outfile)s.log | gzip > %(outfile)s'''
    P.run()

#########################################################################
#########################################################################
#########################################################################


@transform([x for x in glob.glob("*.fastq.gz") + glob.glob("*.fastq.1.gz") + glob.glob("*.fastq.2.gz")], regex(r"(\S+).(fastq.1.gz|fastq.gz|fastq.2.gz|csfasta.gz)"), r"replaced.\1.\2")
def replaceBaseWithN(infile, outfile):
    '''replaces the specified base with N'''

    to_cluster = True
    statement = '''python %(scriptsdir)s/fastq2N.py -i %(infile)s %(replace_options)s'''
    P.run()

#########################################################################
#########################################################################
#########################################################################
#########################################################################


@follows(loadProcessingSummary, loadAllProcessingSummary)
def full():
    '''process (filter,trim) reads.'''
    pass

#########################################################################


@follows(loadFastqc, loadFastqcSummary)
def readqc():
    pass

#########################################################################


@follows(loadFilteringSummary)
def cleanData():
    pass

#########################################################################


@follows()
def publish():
    '''publish files.'''
    P.publish_report()


@follows(mkdir("report"))
def build_report():
    '''build report from scratch.'''

    E.info("starting documentation build process from scratch")
    P.run_report(clean=True)


@follows(mkdir("report"))
def update_report():
    '''update report.'''

    E.info("updating documentation")
    P.run_report(clean=False)

if __name__ == "__main__":
    sys.exit(P.main(sys.argv))
