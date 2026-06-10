use pyo3::prelude::*;
use std::collections::HashMap;

/// HEALPix ring-ordered grid mapper.
/// Mirrors `polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix.HealpixGridMapper`.
#[pyclass]
#[derive(Clone)]
pub struct HealpixGridMapper {
    base_axis: String,
    mapped_axes: Vec<String>,
    resolution: usize,
    pub md5_hash: Option<String>,
    axis_reversed: HashMap<String, bool>,
    first_axis_vals_cache: Vec<f64>,
}

// ─── internal helpers ──────────────────────────────────────────────────────

fn healpix_nj(i: usize, resolution: usize) -> usize {
    assert!(resolution > 0);
    let ni = 4 * resolution - 1;
    assert!(i < ni, "ring index {} out of range (ni={})", i, ni);

    if i < resolution {
        4 * (i + 1)
    } else if i < 3 * resolution {
        4 * resolution
    } else {
        healpix_nj(ni - 1 - i, resolution)
    }
}

fn healpix_longitudes(i: usize, resolution: usize) -> Vec<f64> {
    let nj = healpix_nj(i, resolution);
    let step = 360.0 / nj as f64;

    // shift by half-step when in polar caps OR when (i + resolution) is odd
    let start = if i < resolution
        || (3 * resolution - 1 < i)
        || ((i + resolution) % 2 == 1)
    {
        step / 2.0
    } else {
        0.0
    };

    (0..nj).map(|k| start + k as f64 * step).collect()
}

fn compute_first_axis_vals(resolution: usize) -> Vec<f64> {
    let rad2deg = 180.0 / std::f64::consts::PI;
    let size = 4 * resolution - 1;
    let mut vals = vec![0.0f64; size];

    // Polar caps (rings 1 .. resolution-1, 0-indexed: 0 .. resolution-2)
    for i in 1..resolution {
        let i_f = i as f64;
        let r_f = resolution as f64;
        let val = 90.0 - rad2deg * (1.0 - (i_f * i_f) / (3.0 * r_f * r_f)).acos();
        vals[i - 1] = val;
        vals[size - i] = -val;
    }

    // Equatorial belts (rings resolution .. 2*resolution-1, 0-indexed)
    for i in resolution..(2 * resolution) {
        let i_f = i as f64;
        let r_f = resolution as f64;
        let val = 90.0 - rad2deg * ((4.0 * r_f - 2.0 * i_f) / (3.0 * r_f)).acos();
        vals[i - 1] = val;
        vals[size - i] = -val;
    }

    // Equator
    vals[2 * resolution - 1] = 0.0;

    vals
}

/// Accumulate ring sizes up to (but not including) `first_idx`, then add `second_idx`.
fn axes_idx_to_healpix_idx(resolution: usize, first_idx: usize, second_idx: usize) -> usize {
    let mut idx = 0usize;

    for i in 0..(resolution - 1) {
        if i != first_idx {
            idx += 4 * (i + 1);
        } else {
            idx += second_idx;
            return idx;
        }
    }

    for i in (resolution - 1)..(3 * resolution) {
        if i != first_idx {
            idx += 4 * resolution;
        } else {
            idx += second_idx;
            return idx;
        }
    }

    for i in (3 * resolution)..(4 * resolution - 1) {
        if i != first_idx {
            idx += 4 * (4 * resolution - 1 - i);
        } else {
            idx += second_idx;
            return idx;
        }
    }

    idx
}

// ─── PyO3 impl ─────────────────────────────────────────────────────────────

#[pymethods]
impl HealpixGridMapper {
    #[new]
    #[pyo3(signature = (base_axis, mapped_axes, resolution, md5_hash=None, local_area=None, axis_reversed=None, mapper_options=None))]
    pub fn new(
        base_axis: String,
        mapped_axes: Vec<String>,
        resolution: usize,
        md5_hash: Option<String>,
        local_area: Option<Vec<f64>>,
        axis_reversed: Option<HashMap<String, bool>>,
        mapper_options: Option<PyObject>,
    ) -> PyResult<Self> {
        // Default axis_reversed: first axis decreasing, second axis increasing
        let axis_reversed = axis_reversed.unwrap_or_else(|| {
            let mut m = HashMap::new();
            m.insert(mapped_axes[0].clone(), true);
            m.insert(mapped_axes[1].clone(), false);
            m
        });

        // Validate (mirror Python __init__ checks)
        if *axis_reversed.get(&mapped_axes[1]).unwrap_or(&false) {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Healpix grid with second axis in decreasing order is not supported",
            ));
        }
        if !*axis_reversed.get(&mapped_axes[0]).unwrap_or(&true) {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Healpix grid with first axis in increasing order is not supported",
            ));
        }

        let first_axis_vals_cache = compute_first_axis_vals(resolution);

        Ok(Self {
            base_axis,
            mapped_axes,
            resolution,
            md5_hash,
            axis_reversed,
            first_axis_vals_cache,
        })
    }

    fn __deepcopy__(&self, _memo: &PyAny) -> Self {
        self.clone()
    }

    /// Returns latitude values for every ring, ordered north-to-south (decreasing).
    pub fn first_axis_vals(&self) -> Vec<f64> {
        self.first_axis_vals_cache.clone()
    }

    /// Return first-axis values in [lower, upper].
    pub fn map_first_axis(&self, lower: f64, upper: f64) -> Vec<f64> {
        self.first_axis_vals_cache
            .iter()
            .copied()
            .filter(|&v| lower <= v && v <= upper)
            .collect()
    }

    /// Return longitude values for the ring whose latitude equals `first_val[0]` (within tol).
    pub fn second_axis_vals(&self, first_val: Vec<f64>) -> PyResult<Vec<f64>> {
        let tol = 1e-8;
        let query = first_val
            .first()
            .copied()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("first_val is empty"))?;

        let idx = self
            .first_axis_vals_cache
            .iter()
            .position(|&v| query - tol <= v && v <= query + tol)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "No first-axis value matching {}",
                    query
                ))
            })?;

        Ok(healpix_longitudes(idx, self.resolution))
    }

    /// Return longitude values for a given ring index (0-based).
    pub fn second_axis_vals_from_idx(&self, first_val_idx: usize) -> Vec<f64> {
        healpix_longitudes(first_val_idx, self.resolution)
    }

    /// Return second-axis values in [lower, upper] for the ring matching `first_val[0]`.
    pub fn map_second_axis(&self, first_val: Vec<f64>, lower: f64, upper: f64) -> PyResult<Vec<f64>> {
        let vals = self.second_axis_vals(first_val)?;
        Ok(vals.into_iter().filter(|&v| lower <= v && v <= upper).collect())
    }

    /// Find the index on the second axis for a given (first_val, second_val) pair.
    pub fn find_second_idx(&self, first_val: Vec<f64>, second_val: f64) -> PyResult<usize> {
        let tol = 1e-10;
        let axis_vals = self.second_axis_vals(first_val)?;
        // bisect_left equivalent: find insertion point for (second_val - tol)
        let idx = axis_vals.partition_point(|&v| v < second_val - tol);
        Ok(idx)
    }

    /// Return the flat HEALPix pixel offset of the first pixel in the ring for `first_val`.
    pub fn unmap_first_val_to_start_line_idx(&self, first_val: f64) -> PyResult<usize> {
        let tol = 1e-8;
        let first_idx = self
            .first_axis_vals_cache
            .iter()
            .position(|&v| first_val - tol <= v && v <= first_val + tol)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "No first-axis value matching {}",
                    first_val
                ))
            })?;

        let resolution = self.resolution;
        let mut idx = 0usize;

        for i in 0..(resolution - 1) {
            if i != first_idx {
                idx += 4 * (i + 1);
            } else {
                return Ok(idx);
            }
        }

        for i in (resolution - 1)..(3 * resolution) {
            if i != first_idx {
                idx += 4 * resolution;
            } else {
                return Ok(idx);
            }
        }

        for i in (3 * resolution)..(4 * resolution - 1) {
            if i != first_idx {
                // Note: Python uses `4 * (4*N - 1 - i + 1)` = `4 * (4*N - i)`
                idx += 4 * (4 * resolution - i);
            } else {
                return Ok(idx);
            }
        }

        Err(pyo3::exceptions::PyValueError::new_err(
            "first_val not found in any ring",
        ))
    }

    /// Map (first_val, second_vals) to flat HEALPix ring indices.
    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> PyResult<Vec<usize>> {
        let tol = 1e-8;
        let query = first_val
            .first()
            .copied()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("first_val is empty"))?;

        let first_idx = self
            .first_axis_vals_cache
            .iter()
            .position(|&v| query - tol <= v && v <= query + tol)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "No first-axis value matching {}",
                    query
                ))
            })?;

        let second_axis = healpix_longitudes(first_idx, self.resolution);
        let mut return_idxs = Vec::with_capacity(second_vals.len());

        for sv in &second_vals {
            let second_idx = second_axis
                .iter()
                .position(|&v| sv - tol <= v && v <= sv + tol)
                .ok_or_else(|| {
                    pyo3::exceptions::PyValueError::new_err(format!(
                        "No second-axis value matching {}",
                        sv
                    ))
                })?;

            let healpix_index =
                axes_idx_to_healpix_idx(self.resolution, first_idx, second_idx);
            return_idxs.push(healpix_index);
        }

        Ok(return_idxs)
    }

    // ── accessors ────────────────────────────────────────────────────────────

    #[getter]
    pub fn get_base_axis(&self) -> &str {
        &self.base_axis
    }

    #[getter]
    pub fn get_mapped_axes(&self) -> Vec<String> {
        self.mapped_axes.clone()
    }

    #[getter]
    pub fn get_resolution(&self) -> usize {
        self.resolution
    }

    #[getter]
    pub fn get_axis_reversed(&self) -> HashMap<String, bool> {
        self.axis_reversed.clone()
    }
}
