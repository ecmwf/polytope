# TODO: create a slicer object, which computes points inside of the requested shape in the right dimensionality
# for eg, in 2D, we find points inside of the quadtree and in 1D, we find values between bounds
# TODO: to choose the slicer, we need to look at the dimensionality of the grid/axes realistically
# In particular, we would like to be able to detect whether the grid is irregular or not at first,
# and then it's higher-dimensional, otherwise for now assume it's 1D
