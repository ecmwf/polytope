# Getting Started

### Before Installation 

- **Git Large File Storage**

    Polytope uses Git Large File Storage (LFS) to store its large data files. 
    Before installing Polytope, it is thus necessary to install Git LFS locally as well, by following instructions provided [here](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage) for example.

- **Dependencies**

    The Polytope software requires the installation of the eccodes and GDAL libraries.
    It is possible to install both of these dependencies using either a package manager or manually.


### Installation 

Install the polytope software with Python 3 (>=3.7) from GitHub directly with the command

    python3 -m pip install --upgrade git+https://github.com/ecmwf/polytope.git@master

or from Pypi with the command

    python3 -m pip install polytope