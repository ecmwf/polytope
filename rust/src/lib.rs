use pyo3::prelude::*;
pub mod fdb_sort;
pub mod lambert_conformal;
pub mod list_tools;
use pyo3::wrap_pyfunction;

pub mod distance;
use crate::lambert_conformal::{get_latlons_oblate, get_latlons_sphere};

pub mod healpix_nested;

use crate::healpix_nested::{axes_idx_to_healpix_idx_batch, ring_to_nested_batched, first_axis_vals_healpix_nested, unmap, healpix_longitudes};

pub mod octahedral;
use crate::octahedral::{unmap_octahedral, first_axis_vals_octahedral};

pub mod mappers;
pub mod quadtree_mod;
pub mod slicing_tools;

pub mod point_in_polygon;

use crate::point_in_polygon::{extract_point_in_poly, extract_point_in_poly_bbox};

pub mod merger;

#[pymodule]
fn polytope_rs(py: Python, m: &PyModule) -> PyResult<()> {
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
    m.add_class::<merger::DatacubeAxisMerger>()?;
    m.add_class::<mappers::regular::RegularGridMapper>()?;
    m.add_class::<mappers::octahedral::OctahedralGridMapper>()?;
    m.add_class::<mappers::reduced_gaussian::ReducedGaussianGridMapper>()?;
    m.add_class::<mappers::healpix::HealpixGridMapper>()?;
    m.add_class::<mappers::healpix_nested::NestedHealpixGridMapper>()?;
    m.add_class::<mappers::reduced_ll::ReducedLatLonMapper>()?;
    m.add_class::<mappers::local_regular::LocalRegularGridMapper>()?;
    m.add_class::<mappers::unstructured::UnstructuredGridMapper>()?;
    m.add_class::<mappers::lambert_conformal::LambertConformalGridMapper>()?;
    m.add_class::<mappers::irregular::IrregularGridMapper>()?;
    m.add_function(wrap_pyfunction!(fdb_sort::sort_request_ranges, m)?)?;
    m.add_function(wrap_pyfunction!(fdb_sort::expand_compressed_requests, m)?)?;
    m.add_function(wrap_pyfunction!(fdb_sort::sort_request_ranges_flat, m)?)?;
    m.add_function(wrap_pyfunction!(fdb_sort::expand_compressed_requests_flat, m)?)?;
    Ok(())
}

