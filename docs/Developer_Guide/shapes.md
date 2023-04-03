# Mid-level API shapes

Users can request the following shapes from the mid-level API:

#### ConvexPolytope

The *ConvexPolytope* shape is in fact just the low-level API polytope shape, which is also available from the mid-level API. 

This shape takes as input a list of the axes on which it is defined, as well as a list of its vertices. An example ConvexPolytope shape is given by:

    points = [[0, 0], [10, 10], [0, 10]]
    ConvexPolytope(["latitude", "longitude"], points)

<!-- !!! important 
    This shape can be defined on arbitrarily many dimensions. -->

#### Select

The *Select* shape allows selection of individual indices on datacube axes.

This shape takes as input an axis, as well as a list of indices to select. An example Select shape is given by:

    Select("latitude", [10.5, 11.5, 12.5])

<!-- !!! important
    This shape is 1-dimensional and cannot accept more or less than 1 datacube axis in its definition. -->

#### Span 

The *Span* shape allows selection of all indices between a range of values on a datacube axis. 

This shape takes as input an axis, as well as the lower and upper values of the range to select. An example Span shape is given by:

    Span("latitude", 10.5, 11.5)

<!-- !!! important
    This shape is 1-dimensional and cannot accept more or less than 1 datacube axis in its definition. -->

#### All

The *All* shape allows selection of all indices on a datacube axis. 

This shape takes as sole input an axis. An example All shape is given by:

    All("latitude")

<!-- !!! important
    This shape is 1-dimensional and cannot accept more or less than 1 datacube axis in its definition. -->

#### Box

The *Box* shape specifies a box along several datacube axes. In other words, it specifies ranges to extract along an arbitrary number of datacube axes. 

This shape takes as input a list of the box axes, as well as the lower and upper corners of the box. An example Box shape (in 3 dimensions) is given by:

    lower = [5, 10, 0]
    upper = [10, 30, 3]
    Box(["latitude", "longitude", "timestep"], lower, upper)

<!-- !!! important 
    This shape can be defined on arbitrarily many dimensions. -->

#### Disk

The *Disk* shape specifies an ellipse to extract along 2 datacube axes.

This shape takes as input a list of the two ellipse axes, the center point of the ellipse as well as the values of the semi-major and semi-minor axis along this shapes' axes. An example Disk shape is given by:

    center = [15, 15]
    radius = [5, 5]
    Disk(["latitude", "longitude"], center, radius)

!!! note
    This shape is not a true smooth ellipse, but an approximation of an ellipse.
    It is in fact a larger dodecagon (12-sided polygon) which circumscribes the specified ellipse. 
    This implies in particular that it might return some additional points outside of the requested ellipse.

!!! important
    This shape is 2-dimensional and cannot accept more or less than 2 datacube axes in its definition.

#### Ellipsoid

The *Ellipsoid* shape specifies an ellipsoid to extract along 3 datacube axes. It is the 3-dimensional version of the disk shape.

This shape takes as input a list of the three ellipsoid axes, the center point of the ellipsoid as well as the values of the 3 radii along this shapes' axes. An example Ellipsoid shape is given by:

    center = [15, 15, 5]
    radius = [5, 5, 2]
    Ellipsoid(["latitude", "longitude", "altitude"], center, radius)

!!! note 
    This shape is not a true smooth ellipsoid, but an approximation of an ellipsoid. 
    It is in fact a larger icosahedron which circumscribes the specified ellipsoid. 
    This implies in particular that it might return some additional points outside of the requested ellipsoid.

!!! important
    This shape is 3-dimensional and cannot accept more or less than 3 datacube axes in its definition.

#### Polygon

The *Polygon* shape specifies a polygon to extract along 2 datacube axes. 

This shape takes as input a list of the two polygon axes, as well as a list of all of its vertices. An example Polygon shape is given by:

    points = [[1,0], [3,0], [2,3], [3,6], [1,6]]
    Polygon(["latitude", "longitude"], points)

!!! note
    It is possible to request concave polygons using this shape.

!!! important
    This shape is 2-dimensional and cannot accept more or less than 2 datacube axes in its definition.

#### PathSegment

The *PathSegment* shape is defined by a shape which is swept along a straight line between two points.

This shape takes as input the axes along which we sweep, the shape that we sweep, as well as the start and ending points between which we want to sweep.
An example PathSegment shape is given by:

    box = Box(["latitude", "longitude"], [5, 5], [10, 15])
    PathSegment(["latitude", "longitude"], box, [0, 0], [3, 7])

!!! note
    The axes of the swept shape and PathSegment have to match exactly. A PathSegment just sweeps a shape diagonally on the plane on which the swept shape is defined. 
    It can not be used to sweep a shape along any additional dimensions.

<!-- !!! important 
    This shape can be defined on arbitrarily many dimensions. -->

#### Union

The *Union* shape merges an arbitrary number of shapes together into one shape. 

This shape takes as input the axes along which the union will be defined as well as the list of shapes to be merged. An example Union shape is given by:

    shape1 = Box(["latitude", "longitude"], [5, 10], [15, 25])
    shape2 = Disk(["latitude", "longitude"], [15, 30], [10, 5])
    shape3 = Box(["latitude", "longitude"], [30, 35], [45, 50])
    Union(["latitude", "longitude"], shape1, shape2, shape3)

!!! note
    The axes of the merged shape and Union have to match exactly. 

<!-- !!! important 
    This shape can be defined on arbitrarily many dimensions. -->

#### Path

The *Path* shape is defined by a shape which is swept along a polyline defined by multiple points.

This shape takes as input the axes along which we sweep, the shape that we sweep, the points defining the polyline along which we sweep, as well as an option to specify whether the polyline is closed or not. 
An example Path shape is given by:

    box = Box(["latitude", "longitude"], [5, 5], [10, 15])
    Path(["latitude", "longitude"], box, [0, 0], [5, 10], [7, 16], closed=True)

!!! note 
    The closed option is set to False by default, but can be changed to True if needed.

!!! note
    The axes of the swept shape and Path have to match exactly. A Path just sweeps a shape diagonally on the plane on which the swept shape is defined. 
    It can not be used to sweep a shape along any additional dimensions.

<!-- !!! important 
    This shape can be defined on arbitrarily many dimensions. -->



