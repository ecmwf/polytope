# Datacube

Datacubes are multi-dimensional arrays which store data along several "axes" of metadata. 
The Polytope Datacube component provides an interface to such datacubes. 
In particular, it describes essential features of the underlying datacubes, such as their axes, and specifies data querying mechanisms on them.

### Datacube Structure

The datacube does not necessarily have the same dimensionality in all directions. In particular, on some axes, it is possible to have indices which give rise to different subsequent axes or axis indices. 
!!! note "Example"
    In ECMWF's NWP datacube, choosing the "oper" stream will give different "variable" axis indices than when choosing the "wave" stream. Choosing a specific "stream" index thus changes the subsequent choice of "variable" axis indices. 

This suggests that there is a natural axis ordering which we should follow when extracting data. 
Polytope's Datacube component implements such an axis ordering. This in turn ensures that Polytope is able to support all types of branching and non-branching datacubes.

### Datacube Axes

Axes in a datacube refer to the dimensions along which the data is stored. Values along these axes are called indices. 
Polytope distinguishes two main types of axes: the ordered and unordered categorical axes. These two types of axes cannot be handled in the same way by the Slicer component, hence their distinction. 

- **Ordered Axes**

    Ordered axes are axes whose indices can be ordered. On such axes, it is possible to query ranges of indices as well as individual index values. 
    !!! note "Example"
        In ECMWF's NWP datacube, the "latitude" axis is an ordered axis. Indeed, the "latitude" axis stores floating point numbers, which are comparable and can be ordered into numbers of increasing value. 

    There are many different types of ordered axes. More details about the ones currently implemented in Polytope can be found [here](../Developer_Guide/Axis_types.md).
<!-- The different types of currently implemented ordered axes are listed [here](). -->

- **Categorical Axes**

    Categorical axes are axes whose indices cannot be ordered or compared to each other. On such axes, it is only possible to query specific index values.
    !!! note "Example"
        In ECMWF's NWP datacube, the "variable" axis is a categorical axis. Indeed, the "variable" axis stores the names of the available variables such as "temperature" or "wind speed". These name strings are not comparable and can thus not be ordered, but rather form distinct categories.

### Datacube Request Trees

Datacube request trees are a custom tree data structure used to store the successive axis indices found by the Slicer component during the extraction process. They are used to communicate between the Datacube and Slicer components as well as to query specific axis indices from the datacube.