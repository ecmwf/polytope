# Installation

The script automatically places your token in `~/.polytopeapirc` where the client will pick it up. The token is a long-lived ("offline_access") token.

Install **earthkit-data** with python3 (>= 3.8) and ``pip`` as follows:


    python3 -m pip install earthkit-data

The package installed like this is **minimal** supporting only GRIB and NetCDF data and cannot access remote services other than URLs. If you want to use more data types or remote services you need to install the optional Python packages.

To use polytope also install its dependencies.

You can install **earthkit-data** with all the optional Polytope packages in one go by using:


    python3 -m pip install earthkit-data[polytope]

For further details on earthkit-data installation you can visit this page: https://earthkit-data.readthedocs.io/en/latest/install.html.

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

To access ECMWF data a user needs an ECMWF account. This can be created <a href=https://www.ecmwf.int/>https://www.ecmwf.int/</a>. Once created a user can find their key at <a href=https://api.ecmwf.int/v1/key/>https://api.ecmwf.int/v1/key/</a>. 

This should then be placed in their home directory in a file called `~/.polytopeapirc`. Ths file should have the following format:


```
{
    "user_email" : "<user_email>",
    "user_key" : "<user_key>"
}
```

You should now be automatically authenticated when using Polytope Feature Extraction via Earthkit-data.

Once installed and with an api key in place you can follow the <a href="../Quick_Start">Quick Start</a> guide to begin making requests.