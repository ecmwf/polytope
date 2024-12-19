# Installation

Install **earthkit-data** with python3 (>= 3.10) and ``pip`` as follows:


    python3 -m pip install earthkit-data[polytope]

To use covjson functionality also run:

    python3 -m pip install earthkit-data[covjsonkit]

To use any of the visualisations, also install earthkit-plots:

    python3 -m pip install earthkit-plots

Installing like this gives you a **minimal** package which can talk to Polytope. If you want to use more data types or remote services you need to install other optional features of earthkit-data, or just install all of them:

    python3 -m pip install earthkit-data[all]

For further details on earthkit-data installation you can visit this page: <a href=https://earthkit-data.readthedocs.io/en/latest/install.html>https://earthkit-data.readthedocs.io/en/latest/install.html</a>.

We recommend to create a conda environment for your earthkit installation. This can be done as follows:

```
envname=earthkit
conda create -n $envname -c conda-forge -y python=3.10
conda activate $envname

python3 -m pip install earthkit-data[polytope]

# To allow easy use with a jupyter notebook run the following
python3 -m pip install ipykernel
python3 -m ipykernel install --user --name=$envname
```

# Authentication

To access ECMWF data you need an ECMWF account. This can be created <a href=https://www.ecmwf.int/>https://www.ecmwf.int/</a>. Once created, you can find your key at <a href=https://api.ecmwf.int/v1/key/>https://api.ecmwf.int/v1/key/</a>.

**DISCLAIMER**
> *Polytope is currently available for users at the national meteorological services of ECMWF’s Member and Co-operating States.*

Copy your API key into your home directory, in a file called `~/.polytopeapirc`. Ths file should have the following format:


```
{
    "user_email" : "<user_email>",
    "user_key" : "<user_key>"
}
```

You should now be automatically authenticated when using Polytope feature extraction via earthkit-data.

After following these steps, go to the <a href="../Quick_Start">Quick Start</a> guide to begin making requests.