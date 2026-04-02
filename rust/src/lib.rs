use pyo3::prelude::*;
pub mod lambert_conformal;
pub mod list_tools;

pub mod distance;
use crate::lambert_conformal::{get_latlons_oblate, get_latlons_sphere};

pub mod healpix_nested;
use crate::healpix_nested::{
    axes_idx_to_healpix_idx_batch, first_axis_vals_healpix_nested, healpix_longitudes,
    ring_to_nested_batched, unmap,
};

pub mod octahedral;
use crate::octahedral::{first_axis_vals_octahedral, unmap_octahedral};

pub mod quadtree_mod;
pub mod slicing_tools;
use crate::slicing_tools::slice_polytope;

pub mod point_in_polygon;
use crate::point_in_polygon::{extract_point_in_poly, extract_point_in_poly_bbox};

pub mod geometry;
use crate::geometry::nearest_pt;

pub mod reduced_gaussian;
use crate::reduced_gaussian::{
    first_axis_vals_reduced_gaussian, lon_spacing_reduced_gaussian_n320, unmap_reduced_gaussian,
};

pub mod healpix_ring;
use crate::healpix_ring::{
    first_axis_vals_healpix_ring, healpix_ring_longitudes, unmap_healpix_ring,
};

#[pymodule]
fn polytope_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_latlons_sphere, m)?)?;
    m.add_function(wrap_pyfunction!(get_latlons_oblate, m)?)?;
    m.add_function(wrap_pyfunction!(axes_idx_to_healpix_idx_batch, m)?)?;
    m.add_function(wrap_pyfunction!(ring_to_nested_batched, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_healpix_nested, m)?)?;
    m.add_function(wrap_pyfunction!(healpix_longitudes, m)?)?;
    m.add_function(wrap_pyfunction!(unmap, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_octahedral, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_octahedral, m)?)?;
    m.add_class::<quadtree_mod::QuadTree>()?;
    m.add_class::<quadtree_mod::QuadTreeNode>()?;
    m.add_function(wrap_pyfunction!(extract_point_in_poly, m)?)?;
    m.add_function(wrap_pyfunction!(extract_point_in_poly_bbox, m)?)?;
    // N-dimensional polytope slicing (replaces scipy.spatial.ConvexHull hot-path)
    m.add_function(wrap_pyfunction!(slice_polytope, m)?)?;
    // Brute-force k-nearest-neighbour (replaces Python nearest_pt)
    m.add_function(wrap_pyfunction!(nearest_pt, m)?)?;
    // Reduced Gaussian grid mapper
    m.add_function(wrap_pyfunction!(first_axis_vals_reduced_gaussian, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_reduced_gaussian, m)?)?;
    m.add_function(wrap_pyfunction!(lon_spacing_reduced_gaussian_n320, m)?)?;
    // HEALPix ring grid mapper
    m.add_function(wrap_pyfunction!(first_axis_vals_healpix_ring, m)?)?;
    m.add_function(wrap_pyfunction!(healpix_ring_longitudes, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_healpix_ring, m)?)?;
    Ok(())
}
