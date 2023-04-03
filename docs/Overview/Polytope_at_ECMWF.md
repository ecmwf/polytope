# Polytope at ECMWF

Numerical weather prediction (NWP) data produced at ECMWF can be viewed as a high dimensional datacube (6D or 7D). 
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="../images_overview/ecmwf_datacube.png" alt="ECMWF datacube" width="350"/>
    </p>
    </div>

As mentioned in the [overview](../Overview/Overview.md), traditional extraction methods on such a datacube extract so called "bounding boxes" of data where ranges along each axis are specified. Such extraction methods however do not scale well to large datacubes with a large pool of users. As ECMWF's NWP datacube is of the order of petabytes with thousands of users accessing it daily, using these bounding box techniques has become increasingly difficult.  

To alleviate such issues, ECMWF uses Polytope to extract polytopes instead of bounding boxes from its NWP datacube. 
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="../images_overview/ecmwf_polytope.png" alt="Polytope Concept" width="450"/>
    </p>
    </div>

### Accessing ECMWF's Object Store

At ECMWF, Polytope's datacube component is designed specifically to extract data from the [FDB](https://github.com/ecmwf/fdb), ECMWF's domain-specific object store.
Polytope calculates the precise bytes to be extracted from the FDB. 
Knowing the specific bytes to extract then implies that it is possible to only read those bytes from the server. 
This is in contrast to the previous bounding box extraction approach used at ECMWF, where whole fields had to be read each time data was accessed. 
This saves a considerable amount of I/O usage, resulting in improved latency and making ECMWF's data more readily available to a larger audience. 

### Benefits

As just discussed, Polytope helps achieve a considerable reduction in I/O usage. 
Another benefit of using Polytope at ECMWF is that it reduces the need for post-processing on the users side once they receive their data. 
Indeed, users receive exactly the data they want instead of bounding boxes which they then have to cut. 
This is particularly beneficial in weather forecasting applications, where many users are interested in accessing non-orthogonal polytope shapes.