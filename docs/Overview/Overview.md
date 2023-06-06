# Polytope

Polytope provides a novel way of accessing petabyte-scale datacubes. 
In particular, it provides access to a novel feature and data extraction algorithm designed using computational geometry concepts. 
Developed by ECMWF - the European Center for Medium-Range Weather Forecasts - its main aims are to:

- Reduce I/O usage when requesting data from large datacubes and

- Reduce post-processing needs for users after extraction.

### Traditional Extraction Techniques

Traditional data extraction techniques only allow users to access datacubes "orthogonally" by selecting specific values or ranges along datacube dimensions. 
Such data access mechanisms can be seen as extracting so-called "bounding boxes" of data. 
These mechanisms are quite limited however as many user requests cannot be formulated using bounding boxes.  

!!!note "Example"

    Imagine for example someone interested in extracting temperature data over the shape of France. 
    France is not a box shape over latitude and longitude. 
    Using current extraction techniques, this exact request would therefore be impossible and users would instead need to request a bounding box around France.
    The user would thus get back much more data than he truly needs.  

In higher dimensions, this becomes an even bigger challenge with only tiny fractions of the extracted data being useful to users.

### Polytope Extraction Technique

As an alternative, Polytope enables users to access datacubes "non-orthogonally". 
Instead of extracting bounding boxes of data, Polytope has the capability of querying high-dimensional "polytopes" along several axes of a datacube. 
This is much less restrictive than the popular bounding box approach described before.  

!!!note "Example"

    Using Polytope, extracting the temperature over just the shape of France is now trivially possible by specifying the right polytope.
    This returns much less data than by using a bounding box approach.

These polytope-based requests do in fact allow Polytope to fulfill its two main aims. 
Indeed, because polytope requests return only the exact data users need, they significantly reduce I/O usage as less data has to be transmitted.
Moreover, because only the data inside the requested polytope is returned, this method completely removes the challenge of post-processing on the user side, as wanted.