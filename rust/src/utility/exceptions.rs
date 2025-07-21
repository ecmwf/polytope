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


// AxisUnderdefinedError

#[derive(Debug)]
pub struct AxisUnderdefinedError{
    axis: Box<dyn DatacubeAxis>,
}

impl AxisUnderdefinedError {
    pub fn new(axis: Box<dyn DatacubeAxis>) -> Self {
        Self {
            axis,
        }
    }
}

impl fmt::Display for AxisUnderdefinedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Axis {:?} is underdefined. It does not appear in any input polytope.",
            self.axis
        )
    }
}

impl Error for AxisUnderdefinedError {}

// AxisNotFoundError

#[derive(Debug)]
pub struct AxisNotFoundError{
    axis: Box<dyn DatacubeAxis>,
}

impl AxisNotFoundError {
    pub fn new(axis: Box<dyn DatacubeAxis>) -> Self {
        Self {
            axis,
        }
    }
}

impl fmt::Display for AxisNotFoundError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Axis {:?} does not exist in the datacube.",
            self.axis
        )
    }
}

impl Error for AxisNotFoundError {}

// UnsliceableShapeError

#[derive(Debug)]
pub struct UnsliceableShapeError{
    axis: Box<dyn DatacubeAxis>,
}

impl UnsliceableShapeError {
    pub fn new(axis: Box<dyn DatacubeAxis>) -> Self {
        Self {
            axis,
        }
    }
}

impl fmt::Display for UnsliceableShapeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Higher-dimensional shape does not support unsliceable axis {:?}.",
            self.axis
        )
    }
}

impl Error for UnsliceableShapeError {}

// BadGridError

#[derive(Debug)]
pub struct BadGridError;

impl fmt::Display for BadGridError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Data on this grid is not supported by Polytope."
        )
    }
}

impl Error for BadGridError {}

// GribJumpNoIndexError

#[derive(Debug)]
pub struct GribJumpNoIndexError;

impl fmt::Display for GribJumpNoIndexError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
             "Feature extraction cannot be performed on this data because no GribJump index has been generated."
        )
    }
}

impl Error for GribJumpNoIndexError {}
