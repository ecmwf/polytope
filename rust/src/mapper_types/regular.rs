use pyo3::prelude::*;
use crate::list_tools::bisect_left_cmp;

/// Compute evenly-spaced latitude values for a global regular lat-lon grid.
/// Returns 2*resolution values.
/// If descending (N→S): 90, 90-inc, …, 90-(2N-1)*inc
/// If ascending  (S→N): -90, -90+inc, …
#[pyfunction]
pub fn first_axis_vals_regular(resolution: usize, descending: bool) -> PyResult<Vec<f64>> {
    let n = 2 * resolution;
    let inc = 90.0 / resolution as f64;
    let mut vals = Vec::with_capacity(n);
    if descending {
        for i in 0..n {
            vals.push(90.0 - i as f64 * inc);
        }
    } else {
        for i in 0..n {
            vals.push(-90.0 + i as f64 * inc);
        }
    }
    Ok(vals)
}

/// Compute evenly-spaced latitude values for a local regular lat-lon grid.
/// Returns first_resolution+1 values from lat_min to lat_max (or reversed).
#[pyfunction]
pub fn first_axis_vals_local_regular(
    lat_min: f64,
    lat_max: f64,
    first_resolution: usize,
    descending: bool,
) -> PyResult<Vec<f64>> {
    let n = first_resolution + 1;
    let inc = (lat_max - lat_min) / first_resolution as f64;
    let mut vals = Vec::with_capacity(n);
    if descending {
        for i in 0..n {
            vals.push(lat_max - i as f64 * inc);
        }
    } else {
        for i in 0..n {
            vals.push(lat_min + i as f64 * inc);
        }
    }
    Ok(vals)
}

/// Unmap (lat, [lons]) → flat grid indices for a global regular lat-lon grid.
///
/// The global regular grid has:
///   - 2*resolution latitude rows
///   - 4*resolution longitude columns per row
///   - flat index = first_idx * 4*resolution + second_idx
///
/// `first_axis_vals` must be pre-computed (ascending or descending order).
/// `descending` indicates whether latitudes run N→S (True) or S→N (False).
#[pyfunction]
pub fn unmap_regular(
    resolution: usize,
    first_axis_vals: Vec<f64>,
    first_val: f64,
    second_vals: Vec<f64>,
    descending: bool,
) -> PyResult<Vec<usize>> {
    let n_lons = 4 * resolution;
    let inc = 90.0 / resolution as f64;
    let tol = 1e-8;

    // Find the latitude index
    let first_idx = if descending {
        // latitudes stored N→S (descending), use bisect_left_cmp with x > y
        let target = first_val - tol;
        let idx = bisect_left_cmp(&first_axis_vals, &target, |x, y| x > y);
        if idx < 0 { 0usize } else { idx as usize }
    } else {
        // latitudes stored S→N (ascending), standard binary search
        let target = first_val - tol;
        let idx = bisect_left_cmp(&first_axis_vals, &target, |x, y| x < y);
        if idx < 0 { 0usize } else { idx as usize }
    };

    // Validate the found latitude matches within tolerance
    if first_idx >= first_axis_vals.len()
        || (first_axis_vals[first_idx] - first_val).abs() > tol
    {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Latitude value {} not found in grid within tolerance {}",
            first_val, tol
        )));
    }

    let mut return_idxs = Vec::with_capacity(second_vals.len());

    for &second_val in &second_vals {
        // For the regular grid, lon index = round(second_val / inc)
        let raw = second_val / inc;
        let second_idx = if (raw - raw.floor()) > (1.0 - tol) {
            raw.ceil() as usize
        } else {
            raw.floor() as usize
        };
        // Clamp to valid range
        let second_idx = second_idx.min(n_lons - 1);
        return_idxs.push(first_idx * n_lons + second_idx);
    }

    Ok(return_idxs)
}

/// Unmap (lat, [lons]) → flat grid indices for a local regular lat-lon grid.
///
/// The local regular grid has:
///   - first_resolution+1 latitude rows
///   - second_resolution+1 longitude columns per row
///   - flat index = first_idx * (second_resolution+1) + second_idx
///
/// `first_axis_vals` and `second_axis_vals` are pre-computed sorted arrays.
/// `descending` indicates whether latitudes run N→S (True) or S→N (False).
#[pyfunction]
pub fn unmap_local_regular(
    first_axis_vals: Vec<f64>,
    second_axis_vals: Vec<f64>,
    first_val: f64,
    second_vals: Vec<f64>,
    descending: bool,
    second_resolution: usize,
) -> PyResult<Vec<usize>> {
    let n_lons = second_resolution + 1;

    // Find latitude index using searchsorted with nearest-neighbour snap
    let first_idx = find_nearest_idx(&first_axis_vals, first_val, descending);

    let mut return_idxs = Vec::with_capacity(second_vals.len());

    for &sv in &second_vals {
        // second axis is always ascending for local_regular
        let second_idx = find_nearest_idx(&second_axis_vals, sv, false);
        let second_idx = second_idx.min(n_lons - 1);
        return_idxs.push(first_idx * n_lons + second_idx);
    }

    Ok(return_idxs)
}

/// Binary-search + nearest-neighbour snap into a sorted axis values array.
/// `descending` = true means the array is stored in descending order.
pub fn find_nearest_idx(vals: &[f64], target: f64, descending: bool) -> usize {
    if vals.is_empty() {
        return 0;
    }
    let n = vals.len();

    // Use binary search on the sorted-ascending projection
    let idx = if descending {
        // Array is descending; use descending comparator
        let idx = bisect_left_cmp(vals, &target, |x, y| x > y);
        if idx < 0 { 0usize } else { (idx as usize).min(n - 1) }
    } else {
        let idx = bisect_left_cmp(vals, &target, |x, y| x < y);
        if idx < 0 { 0usize } else { (idx as usize).min(n - 1) }
    };

    // Nearest-neighbour: compare idx-1 and idx, pick closer
    if idx > 0 && idx < n {
        let left = vals[idx - 1];
        let right = vals[idx];
        if (target - left).abs() <= (target - right).abs() {
            idx - 1
        } else {
            idx
        }
    } else if idx == 0 {
        0
    } else {
        n - 1
    }
}
