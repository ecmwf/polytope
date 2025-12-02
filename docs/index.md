# Welcome to Polytope's documentation!

Polytope is a data extraction service that provides both full field global data and feature extraction software developed by ECMWF. 
It uses concepts of computational geometry to extract n-dimensional polygons (also known as *polytopes*) from datacubes. 

In particular, it can be used to request:

- 2D cut-outs, such as country cut-outs, from a datacube
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="./images/greece.png" alt="Greece cut-out" width="250"/>
    </p>
    </div>

- timeseries from a datacube
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="./images/timeseries.png" alt="Timeseries" width="350"/>
    </p>
    </div>

- more complicated spatio-temporal paths, such as flight paths, from a datacube
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="./images/flight_path.png" alt="Flight path" width="350"/>
    </p>
    </div>

- and many more high-dimensional shapes in arbitrary dimensions...

<!-- <div style="text-align:center">
<div class="note", style="border: 1px solid black">
Note that Polytope reads only the user-requested data, instead of whole fields. Importantly, this implies a significant decrease of the I/O usage when reading data from a datacube.
</div>
</div> -->

!!! important
    Note that Polytope reads only the user-requested data, instead of whole fields. Importantly, this implies a significant decrease of the I/O usage when reading data from a datacube.

Polytope feature extraction consists of the algorithm itself, and the service that uses the algorithm to extract features from ECMWF datacubes. Details on the service can be found in the Polytope service <a href="./Service/Overview">overview</a>, while details on the feature extraction algorithm can be found on the <a href="./Algorithm/Overview/Overview">Polytope algorithm overview</a>.

To learn more about how to use Polytope, refer to the <a href="./Service/Quick_Start">Quickstart page</a>. In particular, see the Quickstart page for a step-by-step example of how to use the Polytope software.
For a more in-depth explanation of how Polytope achieves its feature extraction, refer to the <a href="./Algorithm/Developer_Guide/Overview">Developer Guide</a>.

!!! Warning
    This project is BETA and will be experimental for the foreseeable future. Interfaces and functionality are likely to change. DO NOT use this software in any project/software that is operational.

# Index

### <a href="./Service/Overview">Service</a>
  * <a href="./Service/Overview">Overview</a>
  * <a href="./Service/Installation">Installation</a>
  * <a href="./Service/Quick_Start">Quick Start</a>
  * <a href="./Service/Features/feature">Features</a>
  * <a href="./Service/Full_Fields/Full_Fields">Full Fields</a>
  * <a href="./Service/Examples/Index">Examples</a>

### <a href="./Algorithm/Overview/Overview">Algorithm</a>
  * <a href="./Algorithm/Overview/Overview">Overview</a>
  * <a href="./Algorithm/User_Guide/Getting_started">User Guide</a>
  * <a href="./Algorithm/Developer_Guide/Overview">Developer Guide</a>

### <a href="./Client/Overview">Client</a>
  * <a href="./Client/Overview">Overview</a>
  * <a href="./Client/Rest_api">REST API</a>
  * <a href="./Client/python_cli">Python Library and CLI</a>

### <a href="./Server/Overview">Server</a>
  * <a href="./Server/Overview">Overview</a>
  * <a href="./Server/Design">Design</a>

    
# License

*Polytope* is available under the open source [Apache License](http://www.apache.org/licenses/LICENSE-2.0).
 In applying this license, ECMWF does not waive the privileges and immunities granted to it by virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.




