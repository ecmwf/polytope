use pyo3::prelude::*;

/// Brute-force k-nearest-neighbour search matching Python's `nearest_pt()`.
///
/// `pts_list` : list of candidate groups, each group is `([lat...], [lon...])`.
///   All `(lat, lon)` combinations from each group are considered.
/// `pt`       : the query point `(lat, lon)`.
/// `k`        : number of nearest neighbours to return.
///
/// Returns a list of up to `k` `(lat, lon)` tuples ordered by increasing
/// Euclidean distance to `pt`.  Returns an empty list when `pts_list` is
/// empty or produces no candidate points.
#[pyfunction]
#[pyo3(signature = (pts_list, pt, k=1))]
pub fn nearest_pt(
    pts_list: Vec<(Vec<f64>, Vec<f64>)>,
    pt: (f64, f64),
    k: usize,
) -> PyResult<Vec<(f64, f64)>> {
    // Expand all (lat_vals, lon_vals) groups into flat (lat, lon) pairs
    let mut candidates: Vec<(f64, f64)> = Vec::new();
    for (lat_vals, lon_vals) in &pts_list {
        for &lat in lat_vals {
            for &lon in lon_vals {
                candidates.push((lat, lon));
            }
        }
    }

    if candidates.is_empty() {
        return Ok(Vec::new());
    }

    // Compute squared L2 distances (no sqrt needed for sorting)
    let mut dist_pts: Vec<(f64, (f64, f64))> = candidates
        .into_iter()
        .map(|p| {
            let d2 = (p.0 - pt.0) * (p.0 - pt.0) + (p.1 - pt.1) * (p.1 - pt.1);
            (d2, p)
        })
        .collect();

    // Partial sort: only need the first k elements
    dist_pts.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

    let result: Vec<(f64, f64)> = dist_pts.into_iter().take(k).map(|(_, p)| p).collect();

    Ok(result)
}
