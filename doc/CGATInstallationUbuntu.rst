.. _CGATInstallationUbuntu:

=============================
Ubuntu 12.04 LTS Installation
=============================

This installation steps have been tested in Ubuntu 12.04 LTS.The 
:ref:`UbuntuQuickInstallation` uses CGAT supplied scripts for
installation, while :ref:`UbuntuManualInstallation` lists all the 
steps individually.

.. _UbuntuQuickInstallation:

Quick installation
==================

Get a copy of the installation scripts
--------------------------------------

Download and place them into your home directory::

        cd
        wget https://raw.github.com/CGATOxford/cgat/master/install-CGAT-tools.sh
        chmod +x install-CGAT-tools.sh

Install DEB dependencies
------------------------

Become root (or ask your system administrator to do it for you) and run::

        ./install-CGAT-tools.sh --install-os-packages

Install a Python virtual environment with the CGAT code collection
------------------------------------------------------------------- 

Do not be root for this step and run::

        ./install-CGAT-tools.sh --install-python-deps

Test the installation
---------------------

First activate the CGAT virtual environment::

        source $HOME/CGAT-DEPS/virtualenv-1.10.1/cgat-venv/bin/activate

Then, test the cgat command::

        cgat --help

Finish the CGAT virtual environment
-----------------------------------

When you are done, you may deactivate the CGAT virtual environment::

        deactivate


.. _UbuntuManualInstallation:

Manual installation
===================

Install DEB dependencies
------------------------

You can either install them one by one or all at the same time with ``apt-get``::

        apt-get install gcc                  # required by python
        apt-get install zlib1g-dev           # required by virtualenv
        apt-get install libssl-dev           # required by pip
        apt-get install libbz2-dev           # required by bx-python
        apt-get install c++                  # required by pybedtools
        apt-get install libfreetype6-dev     # required by matplotlib
        apt-get install libpng12-dev         # required by matplotlib
        apt-get install libblas-dev          # required by scipy
        apt-get install libatlas-dev         # required by scipy
        apt-get install liblapack-dev        # required by scipy
        apt-get install gfortran             # required by scipyi
        apt-get install libpq-dev            # required by PyGreSQL
        apt-get install r-base-dev           # required by rpy2
        apt-get install libreadline-dev      # required by rpy2
        apt-get install libmysqlclient-dev   # required by MySQL-python
        apt-get install libboost-dev         # required by alignlib
        apt-get install libsqlite3-dev       # required by CGAT
        apt-get install mercurial            # required by bx-python

Build Python 2.7.5
------------------

Download and build your own, isolated Python installation::

        cd
        mkdir CGAT
        wget http://www.python.org/ftp/python/2.7.5/Python-2.7.5.tgz
        tar xzvf Python-2.7.5.tgz
        rm Python-2.7.5.tgz
        cd Python-2.7.5
        ./configure --prefix=$HOME/CGAT/Python-2.7.5
        make
        make install
        cd
        rm -rf Python-2.7.5

Create a virtual environment
----------------------------

Create an isolated virtual environment where all your Python packages will be installed::

        cd
        cd CGAT
        wget --no-check-certificate https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.1.tar.gz
        tar xvfz virtualenv-1.10.1.tar.gz
        rm virtualenv-1.10.1.tar.gz
        cd virtualenv-1.10.1
        $HOME/CGAT/Python-2.7.5/bin/python virtualenv.py cgat-venv
        source cgat-venv/bin/activate

Install Python dependencies
---------------------------

Use pip to install all the packages on which CGAT Code Collection depends on::

        pip install cython
        pip install numpy
        pip install pysam
        pip install https://bitbucket.org/james_taylor/bx-python/get/tip.tar.bz2
        pip install biopython
        pip install pybedtools
        pip install matplotlib
        pip install scipy
        pip install -r https://raw.github.com/CGATOxford/cgat/master/requires.txt
        pip install --upgrade setuptools
        pip install CGAT

Test CGAT Code Collection
-------------------------

If everything went fine with the previous steps you should be able to execute
the following command::

        cgat --help

Finish the CGAT virtual environment
-----------------------------------

When you are done, you may deactivate the CGAT virtual environment::

        deactivate


