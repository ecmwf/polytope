# APIs

The Polytope software has 3 API levels: the high-, mid- and low-level APIs. 
Each level can be used to request different types of shapes from the datacube. 
This choice of levels makes the Polytope software flexible for various types of users, from users who want an easy-to-use software to users who prefer a higher level of precision in their shape definition.
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="../images/Polytope_APIs_3.png" alt="Polytope Components" width="650"/>
    </p>
    </div>

### High-level API
The high-level API supports domain-specific requests. For meteorological use cases, like for ECMWF's weather datacube, this includes timeseries or spatio-temporal flight paths for example. 

An example request on this API level looks like: 

### Mid-level API
The mid-level API supports primitive shapes, such as boxes or disks, as well as constructive geometry, such as unions or paths.

An example request on this API level looks like:

    # A primitive shape request

    box = Box(["latitude", "longitude"], [0, 0], [10, 10])
    request = Request(box)

or using constructive geometry:

    # A constructive geometry request

    box1 = Box(["latitude", "longitude"], [0, 0], [10, 10])
    box2 = Box(["latitude", "longitude"], [10, 10], [20, 20])
    union = Union(["latitude", "longitude"], box1, box2)
    request = Request(union)

For an exhaustive list of all shapes which can be requested using this API level, click [here](../Developer_Guide/shapes.md).

### Low-level API
The low-level API supports raw convex polytope requests. Polytopes here are defined as a list of their vertices. 

An example request on this API level looks like: 

    points = [[0,0], [10,10], [0,10]]
    polytope = ConvexPolytope(["latitude", "longitude"], points)
    request = Request(polytope)

!!! note
    Note that these API levels are built one on top of another. In particular, the high-level API uses the mid-level API, which itself uses the low-level API.