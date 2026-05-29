use pyo3::prelude::*;
use std::collections::HashMap;
use std::f64::consts::PI;

use crate::list_tools::bisect_left_cmp;
use crate::mappers::data::octahedral_n1280::OCTAHEDRAL_N1280_LATS;
use crate::mappers::data::octahedral_n2560::OCTAHEDRAL_N2560_LATS;

// ── helpers (mirror existing octahedral.rs logic) ────────────────────────────

fn gauss_first_guess(resolution: usize) -> Vec<f64> {
    let gvals: [f64; 50] = [
        2.4048255577e0, 5.5200781103e0, 8.6537279129e0, 11.7915344391e0,
        14.9309177086e0, 18.0710639679e0, 21.2116366299e0, 24.3524715308e0,
        27.4934791320e0, 30.6346064684e0, 33.7758202136e0, 36.9170983537e0,
        40.0584257646e0, 43.1997917132e0, 46.3411883717e0, 49.4826098974e0,
        52.6240518411e0, 55.7655107550e0, 58.9069839261e0, 62.0484691902e0,
        65.1899648002e0, 68.3314693299e0, 71.4729816036e0, 74.6145006437e0,
        77.7560256304e0, 80.8975558711e0, 84.0390907769e0, 87.1806298436e0,
        90.3221726372e0, 93.4637187819e0, 96.6052679510e0, 99.7468198587e0,
        102.8883742542e0, 106.0299309165e0, 109.1714896498e0, 112.3130502805e0,
        115.4546126537e0, 118.5961766309e0, 121.7377420880e0, 124.8793089132e0,
        128.0208770059e0, 131.1624462752e0, 134.3040166383e0, 137.4455880203e0,
        140.5871603528e0, 143.7287335737e0, 146.8703076258e0, 150.0118824570e0,
        153.1534580192e0, 156.2950342685e0,
    ];
    let mut vals = Vec::with_capacity(resolution);
    for i in 0..resolution {
        if i < gvals.len() {
            vals.push(gvals[i]);
        } else {
            vals.push(vals[i - 1] + PI);
        }
    }
    vals
}

fn compute_gauss_lats(resolution: usize) -> Vec<f64> {
    let precision = 1.0e-14;
    let nval = resolution * 2;
    let rad2deg = 180.0 / PI;
    let convval = 1.0 - ((2.0 / PI).powi(2)) * 0.25;
    let vals = gauss_first_guess(resolution);
    let mut new_vals = vec![0.0_f64; nval];
    let denom = (((nval as f64 + 0.5).powi(2)) + convval).sqrt();

    for jval in 0..resolution {
        let mut root = (vals[jval] / denom).cos();
        let mut conv = 1.0_f64;
        while conv.abs() >= precision {
            let mut mem2 = 1.0_f64;
            let mut mem1 = root;
            let mut legfonc = 0.0_f64;
            for legi in 0..nval {
                legfonc = ((2.0 * (legi as f64 + 1.0) - 1.0) * root * mem1
                    - legi as f64 * mem2)
                    / (legi as f64 + 1.0);
                mem2 = mem1;
                mem1 = legfonc;
            }
            let denom_inner = nval as f64 * (mem2 - root * legfonc) / (1.0 - root * root);
            conv = legfonc / denom_inner;
            root -= conv;
        }
        let asin_root = root.asin() * rad2deg;
        new_vals[jval] = asin_root;
        new_vals[nval - 1 - jval] = -asin_root;
    }
    new_vals
}

fn create_first_idx_map(resolution: usize) -> Vec<usize> {
    let mut map = vec![0usize; 2 * resolution];
    let mut idx = 0usize;
    for i in 0..(2 * resolution) {
        map[i] = idx;
        if i <= resolution - 1 {
            idx += 20 + 4 * i;
        } else {
            let mut j = i - resolution + 1;
            if j == 1 {
                idx += 16 + 4 * resolution;
            } else {
                j -= 1;
                idx += 16 + 4 * (resolution - j);
            }
        }
    }
    map
}

/// Compute (second_axis_spacing, raw_first_idx+1) for a given latitude.
/// `first_val` is a slice where `first_val[0]` is the latitude value.
fn second_axis_spacing_fn(
    resolution: usize,
    first_val: &[f64],
    first_axis_vals: &[f64],
) -> (f64, usize) {
    let tol = 1e-10;
    let target = first_val[0] - tol;
    let _first_idx = bisect_left_cmp(first_axis_vals, &target, |x, y| x > y);
    let raw = if _first_idx < 0 { 0usize } else { _first_idx as usize };
    let mut fi = raw;
    if fi >= resolution {
        fi = (2 * resolution) - 1 - fi;
    }
    fi += 1;
    let npoints = 4 * fi + 16;
    let spacing = 360.0 / npoints as f64;
    (spacing, (_first_idx + 1) as usize)
}

fn find_second_axis_idx_fn(
    resolution: usize,
    first_val: &[f64],
    second_val: f64,
    first_axis_vals: &[f64],
) -> (usize, usize) {
    let (spacing, first_idx) = second_axis_spacing_fn(resolution, first_val, first_axis_vals);
    let tol = 1e-8;
    let div = second_val / spacing;
    let div_floor = div.floor() as usize;
    let second_idx = if div > (div_floor as f64 + 1.0 - tol) {
        div_floor + 1
    } else {
        div_floor
    };
    (first_idx, second_idx)
}

// ── pyclass ──────────────────────────────────────────────────────────────────

#[pyclass]
pub struct OctahedralGridMapper {
    base_axis: String,
    mapped_axes: Vec<String>,
    resolution: usize,
    md5_hash: Option<String>,
    axis_reversed: HashMap<String, bool>,
    first_axis_vals_cache: Vec<f64>,
    first_idx_map: Vec<usize>,
}

#[pymethods]
impl OctahedralGridMapper {
    #[new]
    pub fn new(
        base_axis: String,
        mapped_axes: Vec<String>,
        resolution: usize,
        md5_hash: Option<String>,
        axis_reversed: Option<HashMap<String, bool>>,
    ) -> PyResult<Self> {
        let first_axis_vals_cache = match resolution {
            1280 => OCTAHEDRAL_N1280_LATS.to_vec(),
            2560 => OCTAHEDRAL_N2560_LATS.to_vec(),
            _ => compute_gauss_lats(resolution),
        };

        let first_idx_map = create_first_idx_map(resolution);

        // Default axis_reversed: first mapped axis reversed (True), second not
        let axis_reversed = axis_reversed.unwrap_or_else(|| {
            let mut m = HashMap::new();
            if mapped_axes.len() >= 2 {
                m.insert(mapped_axes[0].clone(), true);
                m.insert(mapped_axes[1].clone(), false);
            }
            m
        });

        Ok(OctahedralGridMapper {
            base_axis,
            mapped_axes,
            resolution,
            md5_hash,
            axis_reversed,
            first_axis_vals_cache,
            first_idx_map,
        })
    }

    /// Return all latitude values for the first axis.
    pub fn first_axis_vals(&self) -> Vec<f64> {
        self.first_axis_vals_cache.clone()
    }

    /// Return latitude values in [lower, upper] (inclusive, first axis is reversed/descending).
    pub fn map_first_axis(&self, lower: f64, upper: f64) -> Vec<f64> {
        let axis_lines = &self.first_axis_vals_cache;
        // first axis is in decreasing order (north-to-south)
        let end_idx = bisect_left_cmp(axis_lines, &lower, |x, y| x > y) + 1;
        let start_idx = {
            // bisect_right for upper in descending order
            let mut lo = 0isize;
            let mut hi = axis_lines.len() as isize;
            while lo < hi {
                let mid = lo + (hi - lo) / 2;
                if axis_lines[mid as usize] > upper {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            lo as usize
        };
        let end_idx = end_idx.max(0) as usize;
        if start_idx > end_idx || end_idx > axis_lines.len() {
            return vec![];
        }
        axis_lines[start_idx..end_idx].to_vec()
    }

    /// Return longitude values for a given latitude row.
    /// `first_val` is a list with one element (the latitude).
    pub fn second_axis_vals(&self, first_val: Vec<f64>) -> Vec<f64> {
        let (spacing, _) =
            second_axis_spacing_fn(self.resolution, &first_val, &self.first_axis_vals_cache);
        let npoints = (360.0 / spacing).round() as usize;
        (0..npoints).map(|i| i as f64 * spacing).collect()
    }

    /// Return longitude values for the given latitude row filtered to [lower, upper].
    pub fn map_second_axis(&self, first_val: Vec<f64>, lower: f64, upper: f64) -> Vec<f64> {
        let (spacing, _) =
            second_axis_spacing_fn(self.resolution, &first_val, &self.first_axis_vals_cache);
        let start_idx = (lower / spacing) as usize;
        let end_idx = (upper / spacing) as usize + 1;
        (start_idx..end_idx).map(|i| i as f64 * spacing).collect()
    }

    /// Return the second axis index (0-based longitude index) for `second_val`
    /// at the row of `first_val`.
    pub fn find_second_idx(&self, first_val: Vec<f64>, second_val: f64) -> usize {
        let (spacing, _) =
            second_axis_spacing_fn(self.resolution, &first_val, &self.first_axis_vals_cache);
        let tol = 1e-10;
        let div = second_val / spacing;
        let div_floor = div.floor() as usize;
        if div > (div_floor as f64 + 1.0 - tol) {
            div_floor + 1
        } else {
            div_floor
        }
    }

    /// Convert (first_idx, second_idx) 1-based indices to flat octahedral grid index.
    pub fn axes_idx_to_octahedral_idx(&self, first_idx: usize, second_idx: usize) -> usize {
        self.first_idx_map[first_idx - 1] + second_idx
    }

    /// Return the flat start index for the row containing `first_val`.
    pub fn unmap_first_val_to_start_line_idx(&self, first_val: Vec<f64>) -> usize {
        let (_, raw_first_idx) =
            second_axis_spacing_fn(self.resolution, &first_val, &self.first_axis_vals_cache);
        // raw_first_idx is 1-based index; first_idx_map is 0-indexed
        self.first_idx_map[raw_first_idx - 1]
    }

    /// For each (first_val, second_val) pair, return the flat octahedral grid index.
    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> Vec<usize> {
        second_vals
            .iter()
            .map(|&sv| {
                let (fi, si) = find_second_axis_idx_fn(
                    self.resolution,
                    &first_val,
                    sv,
                    &self.first_axis_vals_cache,
                );
                self.axes_idx_to_octahedral_idx(fi, si)
            })
            .collect()
    }
}
