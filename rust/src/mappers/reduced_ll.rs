use pyo3::prelude::*;
use std::collections::HashMap;

use crate::mappers::data::reduced_ll_1441::REDUCED_LL_1441_LON_SPACING;
use crate::mappers::data::reduced_ll_3601::REDUCED_LL_3601_LON_SPACING;

#[pyclass]
pub struct ReducedLatLonMapper {
    #[pyo3(get)]
    pub base_axis: String,
    #[pyo3(get)]
    pub mapped_axes: Vec<String>,
    #[pyo3(get)]
    pub resolution: usize,
    #[pyo3(get)]
    pub md5_hash: Option<String>,
    pub axis_reversed_first: bool,
    pub axis_reversed_second: bool,
    pub first_axis_vals_cache: Vec<f64>,
}

impl ReducedLatLonMapper {
    fn lon_spacing_slice(&self) -> &'static [u32] {
        if self.resolution == 1441 {
            &REDUCED_LL_1441_LON_SPACING
        } else {
            &REDUCED_LL_3601_LON_SPACING
        }
    }

    fn get_first_idx(&self, first_val: f64) -> Option<usize> {
        let tol = 1e-8;
        self.first_axis_vals_cache
            .iter()
            .position(|&v| (v - first_val).abs() < tol)
    }

    fn axes_idx_to_reduced_ll_idx(&self, first_idx: usize, second_idx: usize) -> usize {
        let lon_spacing = self.lon_spacing_slice();
        let mut idx = 0usize;
        for i in 0..self.resolution {
            if i != first_idx {
                idx += lon_spacing[i] as usize;
            } else {
                idx += second_idx;
                return idx;
            }
        }
        idx
    }
}

#[pymethods]
impl ReducedLatLonMapper {
    #[new]
    pub fn new(
        base_axis: String,
        mapped_axes: Vec<String>,
        resolution: usize,
        md5_hash: Option<String>,
        axis_reversed: Option<HashMap<String, bool>>,
    ) -> PyResult<Self> {
        let (axis_reversed_first, axis_reversed_second) = match axis_reversed {
            Some(ref map) => {
                let first = *map.get(&mapped_axes[0]).unwrap_or(&false);
                let second = *map.get(&mapped_axes[1]).unwrap_or(&false);
                (first, second)
            }
            None => (false, false),
        };

        if axis_reversed_first {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Reduced lat-lon grid with first axis in decreasing order is not supported",
            ));
        }
        if axis_reversed_second {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Reduced lat-lon grid with second axis in decreasing order is not supported",
            ));
        }

        let start_lat: f64 = if resolution == 3601 { 89.973092 } else { 90.0 };
        let res_step = 180.0 / (resolution as f64 - 1.0);
        let first_axis_vals_cache: Vec<f64> = (0..resolution)
            .map(|i| {
                let raw = start_lat - i as f64 * res_step;
                // round to 12 decimal places like Python
                (raw * 1e12).round() / 1e12
            })
            .collect();

        let md5 = md5_hash.or_else(|| {
            if resolution == 3601 {
                Some("225e56fb2fdee272ca226dc265d08a0a".to_string())
            } else {
                None
            }
        });

        Ok(ReducedLatLonMapper {
            base_axis,
            mapped_axes,
            resolution,
            md5_hash: md5,
            axis_reversed_first,
            axis_reversed_second,
            first_axis_vals_cache,
        })
    }

    pub fn first_axis_vals(&self) -> Vec<f64> {
        self.first_axis_vals_cache.clone()
    }

    pub fn map_first_axis(&self, lower: f64, upper: f64) -> Vec<f64> {
        self.first_axis_vals_cache
            .iter()
            .copied()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn second_axis_vals(&self, first_val: Vec<f64>) -> PyResult<Vec<f64>> {
        let fv = first_val[0];
        let first_idx = self.get_first_idx(fv).ok_or_else(|| {
            pyo3::exceptions::PyValueError::new_err(
                "Requested latitude value is not within reduced latitude-longitude grid bounds",
            )
        })?;
        let lon_spacing = self.lon_spacing_slice();
        let n_lons = lon_spacing[first_idx] as usize;
        if n_lons == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Requested latitude value is not within reduced latitude-longitude grid bounds",
            ));
        }
        let second_spacing = 360.0 / n_lons as f64;
        Ok((0..n_lons).map(|i| i as f64 * second_spacing).collect())
    }

    pub fn map_second_axis(&self, first_val: Vec<f64>, lower: f64, upper: f64) -> PyResult<Vec<f64>> {
        let vals = self.second_axis_vals(first_val)?;
        Ok(vals.into_iter().filter(|&v| v >= lower && v <= upper).collect())
    }

    pub fn find_second_idx(&self, first_val: Vec<f64>, second_val: f64) -> PyResult<usize> {
        let tol = 1e-10;
        let vals = self.second_axis_vals(first_val)?;
        Ok(vals.partition_point(|&x| x < second_val - tol))
    }

    pub fn unmap_first_val_to_start_line_idx(&self, first_val: f64) -> usize {
        let first_idx = self.get_first_idx(first_val).unwrap_or(0);
        let lon_spacing = self.lon_spacing_slice();
        lon_spacing[..first_idx].iter().map(|&n| n as usize).sum()
    }

    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> PyResult<Vec<usize>> {
        let tol = 1e-8;
        let fv = first_val[0];
        let first_value = self
            .first_axis_vals_cache
            .iter()
            .copied()
            .find(|&v| (v - fv).abs() <= tol)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("first_val not found in grid")
            })?;
        let first_idx = self.get_first_idx(first_value).unwrap_or(0);

        let lon_spacing = self.lon_spacing_slice();
        let n_lons = lon_spacing[first_idx] as usize;
        if n_lons == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Requested latitude value is not within reduced latitude-longitude grid bounds",
            ));
        }
        let second_spacing = 360.0 / n_lons as f64;
        let second_axis: Vec<f64> = (0..n_lons).map(|i| i as f64 * second_spacing).collect();

        let mut return_idxs = Vec::with_capacity(second_vals.len());
        for sv in &second_vals {
            let matched = second_axis
                .iter()
                .copied()
                .find(|&v| (v - sv).abs() <= tol)
                .ok_or_else(|| {
                    pyo3::exceptions::PyValueError::new_err("second_val not found in grid")
                })?;
            let second_idx = second_axis
                .iter()
                .position(|&v| (v - matched).abs() < 1e-12)
                .unwrap_or(0);
            let flat_idx = self.axes_idx_to_reduced_ll_idx(first_idx, second_idx);
            return_idxs.push(flat_idx);
        }
        Ok(return_idxs)
    }
}
