# Building Features

The Polytope software implements a set of base shapes that might be of interest to users. These are detailed [here](../Developer_Guide/shapes.md).

For many applications however, these shapes are not directly of interest and should rather be used as building blocks for more complex and domain-specific "features", such as timeseries or country areas.

The main requirement when building such features in Polytope is that the feature should be defined on all dimensions of the provided datacube.
This implies that, when defining lower-dimensional shapes in higher-dimensional datacubes, the remaining axes still need to be specified within the Polytope request (most likely as *Select* shapes). 

For example, for a given datacube with dimensions "level", "step", "latitude" and "longitude", we could query the following shapes:
- 
