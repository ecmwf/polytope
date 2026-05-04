use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

pub mod list_tools;
pub mod distance;
pub mod quadtree_mod;
pub mod slicing_tools;
pub mod point_in_polygon;

pub mod mapper_types;

use crate::mapper_types::lambert_conformal::{get_latlons_oblate, get_latlons_sphere};
use crate::mapper_types::healpix_nested::{
    axes_idx_to_healpix_idx_batch, ring_to_nested_batched,
    first_axis_vals_healpix_nested, unmap, healpix_longitudes,
};
use crate::mapper_types::octahedral::{unmap_octahedral, first_axis_vals_octahedral};
use crate::mapper_types::regular::{
    first_axis_vals_regular, first_axis_vals_local_regular,
    unmap_regular, unmap_local_regular,
};
use crate::point_in_polygon::{extract_point_in_poly, extract_point_in_poly_bbox};

#[pymodule]
fn polytope_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    // Lambert conformal
    m.add_function(wrap_pyfunction!(get_latlons_sphere, m)?)?;
    m.add_function(wrap_pyfunction!(get_latlons_oblate, m)?)?;
    // HEALPix nested
    m.add_function(wrap_pyfunction!(axes_idx_to_healpix_idx_batch, m)?)?;
    m.add_function(wrap_pyfunction!(ring_to_nested_batched, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_healpix_nested, m)?)?;
    m.add_function(wrap_pyfunction!(healpix_longitudes, m)?)?;
    m.add_function(wrap_pyfunction!(unmap, m)?)?;
    // Octahedral
    m.add_function(wrap_pyfunction!(first_axis_vals_octahedral, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_octahedral, m)?)?;
    // Regular / local regular
    m.add_function(wrap_pyfunction!(first_axis_vals_regular, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_local_regular, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_regular, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_local_regular, m)?)?;
    // Quadtree / point-in-polygon
    m.add_class::<quadtree_mod::QuadTree>()?;
    m.add_class::<quadtree_mod::QuadTreeNode>()?;
    m.add_function(wrap_pyfunction!(extract_point_in_poly, m)?)?;
    m.add_function(wrap_pyfunction!(extract_point_in_poly_bbox, m)?)?;
    Ok(())
}
