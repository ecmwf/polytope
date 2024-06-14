# Building Features

The Polytope software implements a set of base shapes that might be of interest to users. These are detailed [here](../Developer_Guide/shapes.md).

For many applications however, these shapes are not directly of interest and should rather be used as building blocks for more complex and domain-specific "features", such as timeseries or country areas.

The main requirement when building such features in Polytope is that the feature should be defined on all dimensions of the provided datacube.
This implies that, when defining lower-dimensional shapes in higher-dimensional datacubes, the remaining axes still need to be specified within the Polytope request (most likely as *Select* shapes). 

For example, for a given datacube with dimensions "level", "step", "latitude" and "longitude", we could query the following shapes:

- a timeseries of a point which would be defined as
    Request(
        Point(["latitude", "longitude"], [[p1_lat, p1_lon]]), 
        Span("step", start_step, end_step), 
        Select("level", [l1])
        )

- a specific country area which would be defined as 
    Request(
        Polygon([“lat”, “lon”], country_points), 
        Select("step", [s1]),
        Select(“level”, [l1])
        )

- a flight path which would be defined as 
    Request(
        Path(
            [“lat”, “lon”, "level", "step"],
            Box([“lat”, “lon”, "level", "step"], [0, 0, 0, 0], [lat_padding, lon_padding, level_padding, step_padding]),
            flight_points
            )
        )
