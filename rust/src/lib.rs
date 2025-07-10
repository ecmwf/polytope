use pyo3::prelude::*;
pub mod lambert_conformal;
use pyo3::wrap_pyfunction;

use crate::lambert_conformal::{get_latlons_sphere, get_latlons_oblate};

pub mod healpix_nested;

use crate::healpix_nested::{axes_idx_to_healpix_idx_batch, ring_to_nested_batched};


#[pymodule]
fn polytope_rs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_latlons_sphere, m)?)?;
    m.add_function(wrap_pyfunction!(get_latlons_oblate, m)?)?;
    m.add_function(wrap_pyfunction!(axes_idx_to_healpix_idx_batch, m)?)?;
    m.add_function(wrap_pyfunction!(ring_to_nested_batched, m)?)?;
    Ok(())
}