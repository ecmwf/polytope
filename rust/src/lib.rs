use pyo3::prelude::*;
pub mod lambert_conformal;
use pyo3::wrap_pyfunction;

use crate::lambert_conformal::{get_latlons_sphere, get_latlons_oblate};

pub mod healpix_nested;

use crate::healpix_nested::{axes_idx_to_healpix_idx_batch, ring_to_nested_batched, first_axis_vals_healpix_nested};

pub mod datacube;

use crate::datacube::datacube_axis::{IntDatacubeAxis, FloatDatacubeAxis};

pub mod utility;

use crate::utility::exceptions::{BadRequestError, AxisOverdefinedError};




#[pymodule]
fn polytope_rs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_latlons_sphere, m)?)?;
    m.add_function(wrap_pyfunction!(get_latlons_oblate, m)?)?;
    m.add_function(wrap_pyfunction!(axes_idx_to_healpix_idx_batch, m)?)?;
    m.add_function(wrap_pyfunction!(ring_to_nested_batched, m)?)?;
    m.add_function(wrap_pyfunction!(first_axis_vals_healpix_nested, m)?)?;
    Ok(())
}