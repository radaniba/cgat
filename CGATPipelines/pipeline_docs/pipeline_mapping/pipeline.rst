.. Test documentation master file, created by
   sphinx-quickstart on Mon Mar 23 15:27:57 2009.

.. _mappingpipeline:

===========================
Short Read Mapping Pipeline
===========================

Contents:

.. toctree::
   :maxdepth: 2

   pipeline/Methods.rst
   pipeline/Status.rst
   pipeline/Mapping.rst
   pipeline/MappingSummary.rst
   pipeline/MappingContext.rst
   pipeline/MappingAlignmentStatistics.rst
   pipeline/MappingComplexity.rst
   pipeline/ReferenceCoverage.rst
   python/Trackers.rst

.. need to sort out variables. Need to be in conf.py
.. but there should be a generic way to push updates
.. to all reports.

.. ifconfig:: "tophat" in PARAMS['mappers']

   .. toctree::
      pipeline/MappingTophat.rst

.. ifconfig:: "star" in PARAMS['mappers']

   .. toctree::
      pipeline/MappingStar.rst

.. ifconfig:: "tophat" in PARAMS['mappers'] or "star" in PARAMS['mappers'] or "gsnap" in PARAMS['mappers']

   .. toctree::
      pipeline/Validation.rst
 
.. errorlist::

.. warninglist::
  
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


