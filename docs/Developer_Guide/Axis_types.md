# Ordered Axes Types

In the Polytope Datacube component, the ordered axes are classified in function of the data type they store and whether the axes are cyclic or not. 
The different types of currently implemented ordered axes are listed below:

- **IntAxis**: 
    Axis where indices are integers.

- **IntAxisCyclic**:
    Cyclic axis where indices are integers.

- **FloatAxis**:
    Axis where indices are floats.

- **FloatAxisCyclic**:
    Cyclic axis where indices are floats.

- **PandasTimestampAxis**:
    Axis where indices are timestamps.

- **PandasTimedeltaAxis**:
    Axis where indices are timedeltas.

### General Axis Structure

For each Polytope Datacube axis, the following methods and attributes need to be defined:

- **name**

    An attribute storing the name of the axis.  
    This can initially always be set to None as the axes are assigned names during the slicing process.

- **tol**

    An attribute storing the tolerance associated with the axis.  
    This tolerance is used later on when slicing the user-requested shapes along the associated axis.

- **range**

    An attribute storing the range over which the axis is defined.  
    This can initially always be set to None as the axes are assigned ranges during the slicing process.
    !!! note "Example"

        For a cyclic axis like the "longitude" axis which only stores indices between -180 and 180, this will be set to [-180, 180] in the slicing process. For a non-cyclic axis, this will stay defined as None.

- **parse**

    Method which transforms the input value to a continuous type, such as a float or timestamp.


- **to_float**

    Method which transforms the input value from a continuous type to a float.

- **from_float**

    Method which transforms the input value from a float to a continuous type.

<br>
</br>
Additionally, when defining cyclic Polytope Datacube axes, the following methods need to be specified:

- **to_intervals**

    Method which cuts the input range into a list of ranges.  
    Cuts are performed when the axis range would be crossed if we remapped the input range to the axis range.
    !!! note "Example"

        For the "longitude" cyclic axis which only stores indices between -180 and 180, if we input the range [90,540], this method returns the list [[90, 180], [180, 450], [450, 540]].

- **remap_range_to_axis_range**

    Method which maps the input range to its equivalent in the axis range.  
    Note that this method returns a single range instead of a list of ranges because it is only used on input intervals which have a smaller length than the length of the axis range.
    !!! note "Example"

        For the "longitude" cyclic axis which only stores indices between -180 and 180, if we input the range [270, 360], this method returns the range [-90,0].

- **remap_val_to_axis_range**

    Method which remaps the input value to a value in the axis range. 
    !!! note "Example"

        For the "longitude" cyclic axis which only stores indices between -180 and 180, if we input the value 270, this method returns the value -90.

- **remap**

    Method which maps the input range to a list of ranges within the axis range.
    !!! note "Example"

        For the "longitude" cyclic axis which only stores indices between -180 and 180, if we input the range [90,270], this method returns the list [[90, 180], [-180, -90]].

- **offset**

    Method which computes the offset of the input range compared to its equivalent in the axis range. 
    !!! note "Example"

        For the "longitude" cyclic axis which only stores indices between -180 and 180, if we input the range [270, 360], this method returns the value 360.

