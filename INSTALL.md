# dgstools installation guide #

Mark A. Caprio
Department of Physics, University of Notre Dame

+ 08/13/21 (mac): Created.

----------------------------------------------------------------

# 1. Retrieving and installing source

  Change to the directory where you want the repository to be installed,
  e.g.,
  ~~~~~~~~~~~~~~~~
  % cd ~/code
  ~~~~~~~~~~~~~~~~

  Clone the `dgstools` repository.
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % git clone https://github.com/mark-caprio/dgstools.git
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Change your working directory to the repository for the following steps:
  ~~~~~~~~~~~~~~~~
  % cd dgstools
  ~~~~~~~~~~~~~~~~

  Set up the package in your `PYTHONPATH` by running `pip` (or `pip3` on Debian):

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  % pip install --user --editable .
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  a. Subsequently updating source

  ~~~~~~~~~~~~~~~~
  % git pull
  ~~~~~~~~~~~~~~~~
