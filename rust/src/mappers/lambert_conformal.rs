use pyo3::prelude::*;

use crate::lambert_conformal::{get_latlons_oblate, get_latlons_sphere};

#[pyclass]
#[derive(Clone)]
pub struct LambertConformalGridMapper {
    #[pyo3(get)]
    pub is_irregular: bool,
    is_spherical: bool,
    // sphere params
    radius: f64,
    // oblate params
    earth_minor_axis_in_metres: f64,
    earth_major_axis_in_metres: f64,
    // common params
    nx: i32,
    ny: i32,
    dx: f64,
    dy: f64,
    lat_first_in_radians: f64,
    lon_first_in_radians: f64,
    lov_in_radians: f64,
    latin1_in_radians: f64,
    latin2_in_radians: f64,
    lad_in_radians: f64,
    #[pyo3(get)]
    pub md5_hash: Option<String>,
}

#[pymethods]
impl LambertConformalGridMapper {
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
        Python::with_gil(|py| {
            let opts = mapper_options
                .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("mapper_options is required"))?;

            let is_spherical: bool = opts.getattr(py, "is_spherical")?.extract(py)?;

            let radius: f64 = if is_spherical {
                opts.getattr(py, "radius")?.extract(py)?
            } else {
                0.0
            };

            let (earth_minor_axis_in_metres, earth_major_axis_in_metres) = if !is_spherical {
                let minor: f64 = opts.getattr(py, "earthMinorAxisInMetres")?.extract(py)?;
                let major: f64 = opts.getattr(py, "earthMajorAxisInMetres")?.extract(py)?;
                (minor, major)
            } else {
                (0.0, 0.0)
            };

            let nx: i32 = opts.getattr(py, "nx")?.extract(py)?;
            let ny: i32 = opts.getattr(py, "ny")?.extract(py)?;
            let dx: f64 = opts.getattr(py, "Dx")?.extract(py)?;
            let dy: f64 = opts.getattr(py, "Dy")?.extract(py)?;
            let lat_first_in_radians: f64 = opts.getattr(py, "latFirstInRadians")?.extract(py)?;
            let lon_first_in_radians: f64 = opts.getattr(py, "lonFirstInRadians")?.extract(py)?;
            let lov_in_radians: f64 = opts.getattr(py, "LoVInRadians")?.extract(py)?;
            let latin1_in_radians: f64 = opts.getattr(py, "Latin1InRadians")?.extract(py)?;
            let latin2_in_radians: f64 = opts.getattr(py, "Latin2InRadians")?.extract(py)?;
            let lad_in_radians: f64 = opts.getattr(py, "LaDInRadians")?.extract(py)?;

            Ok(LambertConformalGridMapper {
                is_irregular: true,
                is_spherical,
                radius,
                earth_minor_axis_in_metres,
                earth_major_axis_in_metres,
                nx,
                ny,
                dx,
                dy,
                lat_first_in_radians,
                lon_first_in_radians,
                lov_in_radians,
                latin1_in_radians,
                latin2_in_radians,
                lad_in_radians,
                md5_hash: _md5_hash,
            })
        })
    }

    fn __deepcopy__(&self, _memo: &PyAny) -> Self {
        self.clone()
    }

    pub fn grid_latlon_points(&self) -> PyResult<Vec<Vec<f64>>> {
        if self.is_spherical {
            let coords = get_latlons_sphere(
                self.latin1_in_radians,
                self.latin2_in_radians,
                self.radius,
                self.lat_first_in_radians,
                self.lad_in_radians,
                self.lon_first_in_radians,
                self.lov_in_radians,
                self.ny,
                self.nx,
                self.dy,
                self.dx,
            )?;
            Ok(coords.into_iter().map(|p| vec![p[0], p[1]]).collect())
        } else {
            let coords = get_latlons_oblate(
                self.latin1_in_radians,
                self.latin2_in_radians,
                self.earth_minor_axis_in_metres,
                self.earth_major_axis_in_metres,
                self.lat_first_in_radians,
                self.lad_in_radians,
                self.lon_first_in_radians,
                self.lov_in_radians,
                self.ny,
                self.nx,
                self.dy,
                self.dx,
            );
            Ok(coords.into_iter().map(|p| vec![p[0], p[1]]).collect())
        }
    }

    pub fn unmap(
        &self,
        _first_val: Vec<f64>,
        _second_val: f64,
        unmapped_idx: Vec<usize>,
    ) -> usize {
        unmapped_idx[0]
    }
}
