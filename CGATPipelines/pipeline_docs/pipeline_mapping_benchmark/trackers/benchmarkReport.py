import os
import sys
import re
import types
import itertools
import glob

from SphinxReport.Tracker import *
from SphinxReport.odict import OrderedDict as odict

# get from config file
UCSC_DATABASE = "mm9"
EXPORTDIR = "export"

###################################################################
###################################################################
###################################################################
###################################################################
# Run configuration script

from SphinxReport.Utils import PARAMS as P
EXPORTDIR = P['mapping_benchmark_exportdir']
DATADIR = P['mapping_benchmark_datadir']
DATABASE = P['mapping_benchmark_backend']

###########################################################################


class benchmarkTracker(TrackerSQL):

    '''Define convenience tracks for plots'''

    def __init__(self, *args, **kwargs):
        TrackerSQL.__init__(self, *args, backend=DATABASE, **kwargs)


class SingleTableHistogram(TrackerSQL):
    columns = None
    table = None
    group_by = None

    def __init__(self, *args, **kwargs):
        TrackerSQL.__init__(self, *args, **kwargs)

    def __call__(self, track, slice=None):
        data = self.getAll("SELECT %(group_by)s, %(columns)s FROM %(table)s")
        return data
