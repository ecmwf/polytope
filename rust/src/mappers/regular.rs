use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
#[derive(Clone)]
pub struct RegularGridMapper {
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
    pub first_axis_vals: Vec<f64>,
    pub deg_increment: f64,
}

#[pymethods]
impl RegularGridMapper {
    #[new]
    pub fn new(
        base_axis: String,
        mapped_axes: Vec<String>,
        resolution: usize,
        md5_hash: Option<String>,
        local_area: Option<Vec<f64>>,
        axis_reversed: Option<HashMap<String, bool>>,
        mapper_options: Option<PyObject>,
    ) -> PyResult<Self> {
        let deg_increment = 90.0 / resolution as f64;

        let (axis_reversed_first, axis_reversed_second) = match axis_reversed {
            Some(ref map) => {
                let first = *map.get(&mapped_axes[0]).unwrap_or(&true);
                let second = *map.get(&mapped_axes[1]).unwrap_or(&false);
                (first, second)
            }
            None => (true, false),
        };

        if axis_reversed_second {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "axis_reversed for second mapped axis must be False for RegularGridMapper",
            ));
        }

        let n = 2 * resolution;
        let first_axis_vals: Vec<f64> = if axis_reversed_first {
            (0..n).map(|i| 90.0 - i as f64 * deg_increment).collect()
        } else {
            (0..n).map(|i| -90.0 + i as f64 * deg_increment).collect()
        };

        Ok(RegularGridMapper {
            base_axis,
            mapped_axes,
            resolution,
            md5_hash,
            axis_reversed_first,
            axis_reversed_second,
            first_axis_vals,
            deg_increment,
        })
    }

    fn __deepcopy__(&self, _memo: &PyAny) -> Self {
        self.clone()
    }

    pub fn first_axis_vals(&self) -> Vec<f64> {
        self.first_axis_vals.clone()
    }

    pub fn map_first_axis(&self, lower: f64, upper: f64) -> Vec<f64> {
        self.first_axis_vals
            .iter()
            .copied()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn second_axis_vals(&self, _first_val: Vec<f64>) -> Vec<f64> {
        let n = 4 * self.resolution;
        (0..n).map(|i| i as f64 * self.deg_increment).collect()
    }

    pub fn map_second_axis(&self, first_val: Vec<f64>, lower: f64, upper: f64) -> Vec<f64> {
        self.second_axis_vals(first_val)
            .into_iter()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn find_second_idx(&self, first_val: Vec<f64>, second_val: f64) -> usize {
        let tol = 1e-10;
        let vals = self.second_axis_vals(first_val);
        vals.partition_point(|&x| x < second_val - tol)
    }

    pub fn axes_idx_to_regular_idx(&self, first_idx: usize, second_idx: usize) -> usize {
        first_idx * 4 * self.resolution + second_idx
    }

    pub fn unmap_first_val_to_start_line_idx(&self, first_val: f64) -> usize {
        let tol = 1e-8;
        let first_idx = self
            .first_axis_vals
            .iter()
            .position(|&v| (v - first_val).abs() < tol)
            .unwrap_or(0);
        first_idx * 4 * self.resolution
    }

    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> Vec<usize> {
        let tol = 1e-8;
        first_val
            .iter()
            .zip(second_vals.iter())
            .map(|(&fv, &sv)| {
                let first_idx = self
                    .first_axis_vals
                    .iter()
                    .position(|&v| (v - fv).abs() < tol)
                    .unwrap_or(0);
                let second_idx = self.find_second_idx(vec![fv], sv);
                self.axes_idx_to_regular_idx(first_idx, second_idx)
            })
            .collect()
    }
}
