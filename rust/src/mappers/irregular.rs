use pyo3::prelude::*;

use super::lambert_conformal::LambertConformalGridMapper;
use super::unstructured::UnstructuredGridMapper;

enum InnerMapper {
    LambertConformal(LambertConformalGridMapper),
    Unstructured(UnstructuredGridMapper),
}

#[pyclass]
pub struct IrregularGridMapper {
    #[pyo3(get)]
    pub is_irregular: bool,
    inner: InnerMapper,
    #[pyo3(get)]
    pub md5_hash: Option<String>,
}

#[pymethods]
impl IrregularGridMapper {
    #[new]
    #[pyo3(signature = (base_axis, mapped_axes, resolution, md5_hash=None, local_area=None, axis_reversed=None, mapper_options=None))]
    pub fn new(
        base_axis: PyObject,
        mapped_axes: PyObject,
        resolution: PyObject,
        md5_hash: Option<PyObject>,
        local_area: Option<PyObject>,
        axis_reversed: Option<PyObject>,
        mapper_options: Option<PyObject>,
    ) -> PyResult<Self> {
        let grid_type: String = Python::with_gil(|py| -> PyResult<String> {
            let opts = mapper_options
                .as_ref()
                .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("mapper_options is required"))?;
            opts.getattr(py, "type")?.extract(py)
        })?;

        match grid_type.as_str() {
            "lambert_conformal" => {
                let mapper = LambertConformalGridMapper::new(
                    base_axis,
                    mapped_axes,
                    resolution,
                    md5_hash,
                    local_area,
                    axis_reversed,
                    mapper_options,
                )?;
                Ok(IrregularGridMapper {
                    is_irregular: true,
                    inner: InnerMapper::LambertConformal(mapper),
                    md5_hash,
                })
            }
            "unstructured" => {
                let mapper = UnstructuredGridMapper::new(
                    base_axis,
                    mapped_axes,
                    resolution,
                    md5_hash,
                    local_area,
                    axis_reversed,
                    mapper_options,
                )?;
                Ok(IrregularGridMapper {
                    is_irregular: true,
                    inner: InnerMapper::Unstructured(mapper),
                    md5_hash,
                })
            }
            "icon" => Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "icon grid type is not implemented in Rust; use Python fallback",
            )),
            other => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown grid_type: {}",
                other
            ))),
        }
    }

    pub fn grid_latlon_points(&self) -> PyResult<Vec<Vec<f64>>> {
        match &self.inner {
            InnerMapper::LambertConformal(m) => m.grid_latlon_points(),
            InnerMapper::Unstructured(m) => Ok(m.grid_latlon_points()),
        }
    }

    pub fn unmap(
        &self,
        _first_val: f64,
        _second_val: f64,
        unmapped_idx: Vec<usize>,
    ) -> usize {
        unmapped_idx[0]
    }
}
