use pyo3::prelude::*;
use std::collections::HashMap;

use crate::healpix_nested::{
    first_axis_vals_healpix_nested,
    healpix_longitudes,
    ring_to_nested_batched,
    axes_idx_to_healpix_idx_batch,
    unmap as healpix_nested_unmap,
};

/// HEALPix nested-ordered grid mapper.
/// Mirrors `polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix_nested.NestedHealpixGridMapper`.
#[pyclass]
#[derive(Clone)]
pub struct NestedHealpixGridMapper {
    base_axis: String,
    mapped_axes: Vec<String>,
    resolution: usize,
    pub md5_hash: Option<String>,
    axis_reversed: HashMap<String, bool>,
    first_axis_vals_cache: Vec<f64>,
    // Precomputed HEALPix parameters
    nside: isize,
    npix: isize,
    ncap: isize,
    k: isize,
}

// ─── PyO3 impl ─────────────────────────────────────────────────────────────

#[pymethods]
impl NestedHealpixGridMapper {
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

        let first_axis_vals_cache = first_axis_vals_healpix_nested(resolution);

        let nside = resolution as isize;
        let npix = 12 * nside * nside;
        let ncap = (nside * (nside - 1)) << 1;
        let k = (resolution as f64).log2() as isize;

        Ok(Self {
            base_axis,
            mapped_axes,
            resolution,
            md5_hash,
            axis_reversed,
            first_axis_vals_cache,
            nside,
            npix,
            ncap,
            k,
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
                idx += 4 * (4 * resolution - i);
            } else {
                return Ok(idx);
            }
        }

        Err(pyo3::exceptions::PyValueError::new_err(
            "first_val not found in any ring",
        ))
    }

    /// Map (first_val, second_vals) to flat HEALPix nested indices.
    /// Delegates to the standalone `unmap` function in `healpix_nested.rs`.
    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> PyResult<Vec<usize>> {
        let query = first_val
            .first()
            .copied()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("first_val is empty"))?;

        let result = healpix_nested_unmap(
            self.first_axis_vals_cache.clone(),
            query,
            second_vals,
            self.nside,
            self.npix,
            self.ncap,
            self.k,
            self.resolution,
        );

        Ok(result)
    }

    /// Batch convert ring indices to nested indices.
    pub fn ring_to_nested_batched(&self, idxs: Vec<isize>) -> Vec<usize> {
        ring_to_nested_batched(idxs, self.nside, self.npix, self.ncap, self.k)
    }

    /// Batch convert (first_idx, second_idxs) to flat HEALPix ring indices.
    pub fn axes_idx_to_healpix_idx_batch(
        &self,
        first_idx: usize,
        second_idxs: Vec<usize>,
    ) -> Vec<usize> {
        axes_idx_to_healpix_idx_batch(self.resolution, first_idx, second_idxs)
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

    #[getter]
    pub fn get_nside(&self) -> isize {
        self.nside
    }

    #[getter]
    pub fn get_npix(&self) -> isize {
        self.npix
    }

    #[getter]
    pub fn get_ncap(&self) -> isize {
        self.ncap
    }

    #[getter]
    pub fn get_k(&self) -> isize {
        self.k
    }
}
