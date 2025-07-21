use std::error::Error;
use std::fmt;
use std::collections::HashMap;

use crate::datacube::datacube_axis::{DatacubeAxis};

// BadRequestError

#[derive(Debug)]
pub struct BadRequestError{
    pre_path: HashMap<String, String>,
}

impl BadRequestError {
    pub fn new(pre_path: HashMap<String, String>) -> Self {
        Self {
            pre_path,
        }
    }
}

impl fmt::Display for BadRequestError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "No data for {:?} is available on the FDB.",
            self.pre_path
        )
    }
}

impl Error for BadRequestError {}


// AxisOverdefinedError

#[derive(Debug)]
pub struct AxisOverdefinedError{
    axis: Box<dyn DatacubeAxis>,
}

impl AxisOverdefinedError {
    pub fn new(axis: Box<dyn DatacubeAxis>) -> Self {
        Self {
            axis,
        }
    }
}

impl fmt::Display for AxisOverdefinedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Axis {:?} is overdefined. You have used it in two or more input polytopes which cannot form a union (because they span different axes).",
            self.axis
        )
    }
}

impl Error for AxisOverdefinedError {}


// // AxisUnderdefinedError

// class AxisUnderdefinedError(PolytopeError, KeyError):
//     def __init__(self, axis):
//         self.axis = axis
//         self.message = f"Axis {axis} is underdefined. It does not appear in any input polytope."


// // AxisNotFoundError

// class AxisNotFoundError(PolytopeError, KeyError):
//     def __init__(self, axis):
//         self.axis = axis
//         self.message = f"Axis {axis} does not exist in the datacube."

// // UnsliceableShapeError

// class UnsliceableShapeError(PolytopeError, KeyError):
//     def __init__(self, axis):
//         self.axis = axis
//         self.message = f"Higher-dimensional shape does not support unsliceable axis {axis.name}."

// // BadGridError

// class BadGridError(PolytopeError, ValueError):
//     def __init__(self):
//         self.message = "Data on this grid is not supported by Polytope."

// // GribJumpNoIndexError

// class GribJumpNoIndexError(PolytopeError, ValueError):
//     def __init__(self):
//         self.message = (
//             "Feature extraction cannot be performed on this data because no GribJump index has been generated."
//         )