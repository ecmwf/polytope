pub mod quadtree_mod;
pub mod slicing_tools;

use pyo3::prelude::*;
pub mod lambert_conformal;
use pyo3::wrap_pyfunction;

use crate::lambert_conformal::{get_latlons_sphere, get_latlons_oblate};

pub mod point_in_polygon;

use crate::point_in_polygon::{extract_point_in_poly, extract_point_in_poly_bbox};

#[pymodule]
fn polytope_rs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<quadtree_mod::QuadTree>()?;
    m.add_class::<quadtree_mod::QuadTreeNode>()?;
    m.add_function(wrap_pyfunction!(get_latlons_sphere, m)?)?;
    m.add_function(wrap_pyfunction!(get_latlons_oblate, m)?)?;
    m.add_function(wrap_pyfunction!(extract_point_in_poly, m)?)?;
    m.add_function(wrap_pyfunction!(extract_point_in_poly_bbox, m)?)?;
    Ok(())
}