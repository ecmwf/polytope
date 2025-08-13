use pyo3::prelude::*;
pub mod lambert_conformal;
pub mod list_tools;
use pyo3::wrap_pyfunction;

use crate::lambert_conformal::{get_latlons_oblate, get_latlons_sphere};

pub mod healpix_nested;

use crate::healpix_nested::{
    axes_idx_to_healpix_idx_batch, first_axis_vals_healpix_nested, ring_to_nested_batched,
};

pub mod octahedral;
use crate::octahedral::{unmap_octahedral, first_axis_vals_octahedral};

#[pymodule]
fn polytope_rs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_latlons_sphere, m)?)?;
    m.add_function(wrap_pyfunction!(get_latlons_oblate, m)?)?;
    m.add_function(wrap_pyfunction!(axes_idx_to_healpix_idx_batch, m)?)?;
    m.add_function(wrap_pyfunction!(ring_to_nested_batched, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_healpix_nested, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_octahedral, m)?)?;
    m.add_function(wrap_pyfunction!(unmap_octahedral, m)?)?;
    Ok(())
}
