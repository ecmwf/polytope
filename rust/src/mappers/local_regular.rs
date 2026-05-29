use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct LocalRegularGridMapper {
    #[pyo3(get)]
    pub base_axis: String,
    #[pyo3(get)]
    pub mapped_axes: Vec<String>,
    #[pyo3(get)]
    pub first_resolution: usize,
    #[pyo3(get)]
    pub second_resolution: usize,
    #[pyo3(get)]
    pub md5_hash: Option<String>,
    pub axis_reversed_first: bool,
    pub axis_reversed_second: bool,
    pub first_axis_min: f64,
    pub first_axis_max: f64,
    pub second_axis_min: f64,
    pub second_axis_max: f64,
    pub first_deg_increment: f64,
    pub second_deg_increment: f64,
    pub cached_first_axis_vals: Vec<f64>,
    pub cached_second_axis_vals: Vec<f64>,
}

#[pymethods]
impl LocalRegularGridMapper {
    #[new]
    #[pyo3(signature = (base_axis, mapped_axes, resolution, md5_hash=None, local_area=vec![], axis_reversed=None))]
    pub fn new(
        base_axis: String,
        mapped_axes: Vec<String>,
        resolution: PyObject,
        md5_hash: Option<String>,
        local_area: Vec<f64>,
        axis_reversed: Option<HashMap<String, bool>>,
        py: Python<'_>,
    ) -> PyResult<Self> {
        if local_area.len() != 4 {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "Local area grid region not or wrongly specified",
            ));
        }

        let first_axis_min = local_area[0];
        let first_axis_max = local_area[1];
        let second_axis_min = local_area[2];
        let second_axis_max = local_area[3];

        // resolution can be a single int or a list of two ints
        let (first_resolution, second_resolution) =
            if let Ok(list) = resolution.extract::<Vec<usize>>(py) {
                if list.len() >= 2 {
                    (list[0], list[1])
                } else {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "resolution list must have at least 2 elements",
                    ));
                }
            } else {
                let r = resolution.extract::<usize>(py)?;
                (r, r)
            };

        let first_deg_increment = (first_axis_max - first_axis_min) / first_resolution as f64;
        let second_deg_increment = (second_axis_max - second_axis_min) / second_resolution as f64;

        let (axis_reversed_first, axis_reversed_second) = match axis_reversed {
            Some(ref map) => {
                let first = *map.get(&mapped_axes[0]).unwrap_or(&false);
                let second = *map.get(&mapped_axes[1]).unwrap_or(&false);
                (first, second)
            }
            None => (false, false),
        };

        if axis_reversed_second {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Local regular grid with second axis in decreasing order is not supported",
            ));
        }

        // Build first axis vals
        let cached_first_axis_vals: Vec<f64> = if axis_reversed_first {
            (0..=first_resolution)
                .map(|i| first_axis_max - i as f64 * first_deg_increment)
                .collect()
        } else {
            (0..=first_resolution)
                .map(|i| first_axis_min + i as f64 * first_deg_increment)
                .collect()
        };

        // Build second axis vals
        let cached_second_axis_vals: Vec<f64> = (0..=second_resolution)
            .map(|i| second_axis_min + i as f64 * second_deg_increment)
            .collect();

        Ok(LocalRegularGridMapper {
            base_axis,
            mapped_axes,
            first_resolution,
            second_resolution,
            md5_hash,
            axis_reversed_first,
            axis_reversed_second,
            first_axis_min,
            first_axis_max,
            second_axis_min,
            second_axis_max,
            first_deg_increment,
            second_deg_increment,
            cached_first_axis_vals,
            cached_second_axis_vals,
        })
    }

    pub fn first_axis_vals(&self) -> Vec<f64> {
        self.cached_first_axis_vals.clone()
    }

    pub fn map_first_axis(&self, lower: f64, upper: f64) -> Vec<f64> {
        self.cached_first_axis_vals
            .iter()
            .copied()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn second_axis_vals(&self, _first_val: f64) -> Vec<f64> {
        self.cached_second_axis_vals.clone()
    }

    pub fn map_second_axis(&self, first_val: f64, lower: f64, upper: f64) -> Vec<f64> {
        self.second_axis_vals(first_val)
            .into_iter()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn find_second_idx(&self, first_val: f64, second_val: f64) -> usize {
        let tol = 1e-10;
        let vals = self.second_axis_vals(first_val);
        vals.partition_point(|&x| x < second_val - tol)
    }

    pub fn axes_idx_to_regular_idx(&self, first_idx: usize, second_idx: usize) -> usize {
        first_idx * (self.second_resolution + 1) + second_idx
    }

    pub fn unmap_first_val_to_start_line_idx(&self, first_val: f64) -> usize {
        let tol = 1e-8;
        let first_idx = self
            .cached_first_axis_vals
            .iter()
            .position(|&v| (v - first_val).abs() <= tol)
            .unwrap_or(0);
        first_idx * self.second_resolution
    }

    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> Vec<usize> {
        if first_val.is_empty() {
            return vec![];
        }
        let fv = first_val[0];
        let first_array = &self.cached_first_axis_vals;
        let second_array = &self.cached_second_axis_vals;

        // Find first_idx using searchsorted with nearest-neighbour snap
        let first_idx = {
            let mut idx = if self.axis_reversed_first {
                // descending: search on negated array
                first_array.partition_point(|&x| -x < -fv)
            } else {
                first_array.partition_point(|&x| x < fv)
            };
            if idx > 0 && idx < first_array.len() {
                let left_dist = (fv - first_array[idx - 1]).abs();
                let right_dist = (fv - first_array[idx]).abs();
                if left_dist < right_dist {
                    idx -= 1;
                }
            } else if idx == first_array.len() && !first_array.is_empty() {
                idx = first_array.len() - 1;
            }
            idx
        };

        second_vals
            .iter()
            .map(|&sv| {
                let mut second_idx = second_array.partition_point(|&x| x < sv);
                if second_idx > 0 && second_idx < second_array.len() {
                    let left_dist = (sv - second_array[second_idx - 1]).abs();
                    let right_dist = (sv - second_array[second_idx]).abs();
                    if left_dist < right_dist {
                        second_idx -= 1;
                    }
                } else if second_idx == second_array.len() && !second_array.is_empty() {
                    second_idx = second_array.len() - 1;
                }
                first_idx * (self.second_resolution + 1) + second_idx
            })
            .collect()
    }
}
