Polytope Client
====================================

Polytope is an open-source web service designed to provide efficient access to hypercubes of data in scientific analysis workflows, and is able to federate access between hypercubes in distributed computing resources. It is designed to couple data-centric workflows operating across multiple platforms (HPC, cloud) and across multiple distributed sites.

Users can access the Polytope service via the REST API exposed by Polytope, or via the polytope-client Python package. The client includes a Python API and a command line tool (CLI) for accessing Polytope services.

We now recommend that users access the Polytope Service via [earthkit-data](https://earthkit-data.readthedocs.io/en/latest/examples/polytope.html).


Features
--------

* Efficient web-based access to a variety of datacube datasources under a common API
* Robust role-based and attribute-based access control, including quality-of-service limits
* Micro-service design, able to be deployed and scaled on Kubernetes and Docker Swarm
* Compatible and extendable to a variety of authentication providers (e.g. Keycloak, LDAP, SSO)
* Federation of multiple Polytope instances, connecting distributed storage infrastructure
* Server-side polytope-based subsetting and feature extraction


License 
-------

*Polytope* is available under the open source `Apache License`. In applying this licence, ECMWF does not waive the privileges and immunities granted to it by virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.

__ http://www.apache.org/licenses/LICENSE-2.0.html

Polytope has been developed at ECMWF as part of the EU projects [LEXIS](https://lexis-project.eu/web/) and [HiDALGO](https://hidalgo-project.eu/). The LEXIS and HiDALGO projects have received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreements No. 825532 and No. 824115.