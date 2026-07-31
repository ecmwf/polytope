use pyo3::prelude::*;

#[pyclass]
#[derive(Clone)]
pub struct UnstructuredGridMapper {
    #[pyo3(get)]
    pub is_irregular: bool,
    latlon_points: Vec<Vec<f64>>,
    #[pyo3(get)]
    pub md5_hash: Option<String>,
}

#[pymethods]
impl UnstructuredGridMapper {
    #[new]
    #[pyo3(signature = (_base_axis, _mapped_axes, _resolution, _md5_hash=None, _local_area=None, _axis_reversed=None, mapper_options=None))]
    pub fn new(
        _base_axis: PyObject,
        _mapped_axes: PyObject,
        _resolution: PyObject,
        _md5_hash: Option<String>,
        _local_area: Option<PyObject>,
        _axis_reversed: Option<PyObject>,
        mapper_options: Option<PyObject>,
    ) -> PyResult<Self> {
        let latlon_points = Python::with_gil(|py| -> PyResult<Vec<Vec<f64>>> {
            if let Some(opts) = mapper_options {
                let points = opts.getattr(py, "points")?;
                points.extract::<Vec<Vec<f64>>>(py)
            } else {
                Ok(vec![])
            }
        })?;

        Ok(UnstructuredGridMapper {
            is_irregular: true,
            latlon_points,
            md5_hash: _md5_hash,
        })
    }

    fn __deepcopy__(&self, _memo: &PyAny) -> Self {
        self.clone()
    }

    pub fn grid_latlon_points(&self) -> Vec<Vec<f64>> {
        self.latlon_points.clone()
    }

    #[pyo3(signature = (_first_val, _second_val=None, unmapped_idx=None))]
    pub fn unmap(
        &self,
        _first_val: Vec<f64>,
        _second_val: Option<Vec<f64>>,
        unmapped_idx: Option<Vec<usize>>,
    ) -> Vec<usize> {
        unmapped_idx.unwrap_or_default()
    }
}
