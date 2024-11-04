# Getting Started

<!-- ### Before Installation 

- **Git Large File Storage**

    Polytope uses Git Large File Storage (LFS) to store its large data files. 
    Before installing Polytope, it is thus necessary to install Git LFS locally as well, by following instructions provided [here](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage) for example.

- **Dependencies**

    The Polytope software requires the installation of the eccodes and GDAL libraries.
    It is possible to install both of these dependencies using either a package manager or manually. -->

### Installation 

Install the polytope software with Python 3 (>=3.7) from GitHub directly with the command

    python3 -m pip install git+ssh://git@github.com/ecmwf/polytope.git@develop

or from PyPI with the command

    python3 -m pip install polytope-python

### Tests and Examples 

Polytope's tests and examples require some additional dependencies compared to the main Polytope software.

<!-- - **Git Large File Storage**

    Polytope uses Git Large File Storage (LFS) to store large data files used in its tests and examples. 
    To run the tests and examples, it is thus necessary to install Git LFS, by following instructions provided [here](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage) for example. 
    Once Git LFS is installed, individual data files can be downloaded using the command

        git lfs pull --include="*" --exclude=""  -->

- **Additional Dependencies**

    The Polytope tests and examples require additional Python packages compared to the main Polytope algorithm.
    The additional dependencies are provided in the requirements_test.txt and requirements_examples.txt files, which can respectively be found in the examples and tests folders.
    Moreover, Polytope's tests and examples also require the installation of eccodes and GDAL.
    It is possible to install both of these dependencies using either a package manager or manually.