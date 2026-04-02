use pyo3::prelude::*;

/// Number of longitudes on ring `i` (0-indexed) of a HEALPix ring grid with given `resolution`.
fn healpix_ring_nj(i: usize, resolution: usize) -> usize {
    debug_assert!(resolution > 0);
    let ni = 4 * resolution - 1;
    debug_assert!(i < ni);

    if i < resolution {
        4 * (i + 1)
    } else if i < 3 * resolution {
        4 * resolution
    } else {
        // Symmetric south: same count as its north mirror
        healpix_ring_nj(ni - 1 - i, resolution)
    }
}

/// Compute the start index of ring `first_idx` in the flattened HEALPix ring array.
/// This replaces the O(N) loop in Python's `axes_idx_to_healpix_idx`.
fn healpix_ring_start_idx(first_idx: usize, resolution: usize) -> usize {
    let res = resolution;

    if first_idx < res - 1 {
        // North polar cap rings 0 .. res-2
        // Sum of 4*(1) + 4*(2) + ... + 4*(first_idx) = 4 * first_idx*(first_idx+1)/2
        2 * first_idx * (first_idx + 1)
    } else if first_idx < 3 * res {
        // Equatorial belt rings res-1 .. 3*res-1
        // North polar cap total: sum_{i=0}^{res-2} 4*(i+1) = 4*(res-1)*res/2 = 2*(res-1)*res
        let north_total = 2 * (res - 1) * res;
        north_total + (first_idx - (res - 1)) * 4 * res
    } else {
        // South polar cap rings 3*res .. 4*res-2
        // North cap total + equatorial total + south cap rings before first_idx
        let north_total = 2 * (res - 1) * res;
        let equatorial_total = (2 * res + 1) * 4 * res;
        // South cap ring j (relative, 0-indexed from start of south cap) has nj = 4*(res - j - 1)
        // first_idx in global = 3*res + j  => j = first_idx - 3*res
        // Sum of nj for j=0..j_local-1 where j_local = first_idx - 3*res
        let j_local = first_idx - 3 * res;
        // sum_{k=0}^{j_local-1} 4*(res - k - 1) = 4 * sum_{k=0}^{j_local-1} (res-1-k)
        // = 4 * (j_local*(res-1) - j_local*(j_local-1)/2)
        let south_prefix = 4 * (j_local * (res - 1) - j_local * (j_local.saturating_sub(1)) / 2);
        north_total + equatorial_total + south_prefix
    }
}

/// Compute the global ring index for a point at (first_idx, second_idx) in the HEALPix ring grid.
fn axes_idx_to_healpix_ring_idx(first_idx: usize, second_idx: usize, resolution: usize) -> usize {
    healpix_ring_start_idx(first_idx, resolution) + second_idx
}

/// Batch unmap for HEALPix ring grid.
/// Given the precomputed first-axis values, the target first_val, a list of second_vals,
/// and the resolution, returns the flat ring indices for each (first_val, second_val) pair.
#[pyfunction]
pub fn unmap_healpix_ring(
    first_axis_vals: Vec<f64>,
    first_val: f64,
    second_vals: Vec<f64>,
    resolution: usize,
) -> PyResult<Vec<usize>> {
    let tol = 1e-8;

    let first_idx = first_axis_vals
        .iter()
        .enumerate()
        .find(|(_, &v)| (first_val - tol <= v) && (v <= first_val + tol))
        .map(|(idx, _)| idx)
        .ok_or_else(|| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "No matching first-axis value found for first_val={}",
                first_val
            ))
        })?;

    let second_axis = healpix_ring_longitudes(first_idx, resolution);

    let mut results = Vec::with_capacity(second_vals.len());
    for second_val in second_vals {
        let second_idx = second_axis
            .iter()
            .enumerate()
            .find(|(_, &v)| (second_val - tol <= v) && (v <= second_val + tol))
            .map(|(idx, _)| idx)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "No matching second-axis value found for second_val={}",
                    second_val
                ))
            })?;

        results.push(axes_idx_to_healpix_ring_idx(
            first_idx, second_idx, resolution,
        ));
    }

    Ok(results)
}

/// Compute the longitude values for ring `i` of a HEALPix ring grid.
/// Identical to `healpix_longitudes` in healpix_nested.rs but kept local to avoid cross-module coupling.
#[pyfunction]
pub fn healpix_ring_longitudes(i: usize, resolution: usize) -> Vec<f64> {
    let nj = healpix_ring_nj(i, resolution);
    let step = 360.0 / nj as f64;

    let start = if i < resolution || (3 * resolution - 1 < i) || ((i + resolution) % 2 == 1) {
        step / 2.0
    } else {
        0.0
    };

    (0..nj).map(|k| start + k as f64 * step).collect()
}

/// Compute all first-axis (latitude) values for a HEALPix ring grid.
/// Identical algorithm to first_axis_vals_healpix_nested.
#[pyfunction]
pub fn first_axis_vals_healpix_ring(resolution: usize) -> Vec<f64> {
    let rad2deg = 180.0 / std::f64::consts::PI;
    let size = 4 * resolution - 1;
    let mut vals = vec![0.0; size];

    // Polar caps
    for i in 1..resolution {
        let i_f64 = i as f64;
        let res_f64 = resolution as f64;
        let val = 90.0 - rad2deg * (1.0 - (i_f64 * i_f64) / (3.0 * res_f64 * res_f64)).acos();
        vals[i - 1] = val;
        vals[size - i] = -val;
    }

    // Equatorial belts
    for i in resolution..(2 * resolution) {
        let i_f64 = i as f64;
        let res_f64 = resolution as f64;
        let val = 90.0 - rad2deg * ((4.0 * res_f64 - 2.0 * i_f64) / (3.0 * res_f64)).acos();
        vals[i - 1] = val;
        vals[size - i] = -val;
    }

    // Equator
    vals[2 * resolution - 1] = 0.0;

    vals
}
