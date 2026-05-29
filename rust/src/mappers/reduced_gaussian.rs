use pyo3::prelude::*;
use std::collections::HashMap;
use std::f64::consts::PI;

use crate::mappers::data::reduced_gaussian_n320::REDUCED_GAUSSIAN_N320_LATS;

// N320 lon_spacing: 640 entries giving number of longitude points per latitude row
// (north-pole to south-pole order, matching the REDUCED_GAUSSIAN_N320_LATS ordering)
const LON_SPACING_N320: [u32; 640] = [18, 25, 36, 40, 45, 50, 60, 64, 72, 72, 75, 81, 90, 96, 100, 108, 120, 120, 125, 135, 144, 144, 150, 160, 180, 180, 180, 192, 192, 200, 216, 216, 216, 225, 240, 240, 240, 250, 256, 270, 270, 288, 288, 288, 300, 300, 320, 320, 320, 324, 360, 360, 360, 360, 360, 360, 375, 375, 384, 384, 400, 400, 405, 432, 432, 432, 432, 450, 450, 450, 480, 480, 480, 480, 480, 486, 500, 500, 500, 512, 512, 540, 540, 540, 540, 540, 576, 576, 576, 576, 576, 576, 600, 600, 600, 600, 640, 640, 640, 640, 640, 640, 640, 648, 648, 675, 675, 675, 675, 720, 720, 720, 720, 720, 720, 720, 720, 720, 729, 750, 750, 750, 750, 768, 768, 768, 768, 800, 800, 800, 800, 800, 800, 810, 810, 864, 864, 864, 864, 864, 864, 864, 864, 864, 864, 864, 900, 900, 900, 900, 900, 900, 900, 900, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 972, 972, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1024, 1024, 1024, 1024, 1024, 1024, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1152, 1152, 1152, 1152, 1152, 1152, 1152, 1152, 1152, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1215, 1215, 1215, 1215, 1215, 1215, 1215, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1280, 1215, 1215, 1215, 1215, 1215, 1215, 1215, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1152, 1152, 1152, 1152, 1152, 1152, 1152, 1152, 1152, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1125, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1080, 1024, 1024, 1024, 1024, 1024, 1024, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 972, 972, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 900, 900, 900, 900, 900, 900, 900, 900, 864, 864, 864, 864, 864, 864, 864, 864, 864, 864, 864, 810, 810, 800, 800, 800, 800, 800, 800, 768, 768, 768, 768, 750, 750, 750, 750, 729, 720, 720, 720, 720, 720, 720, 720, 720, 720, 675, 675, 675, 675, 648, 648, 640, 640, 640, 640, 640, 640, 640, 600, 600, 600, 600, 576, 576, 576, 576, 576, 576, 540, 540, 540, 540, 540, 512, 512, 500, 500, 500, 486, 480, 480, 480, 480, 480, 450, 450, 450, 432, 432, 432, 432, 405, 400, 400, 384, 384, 375, 375, 360, 360, 360, 360, 360, 360, 324, 320, 320, 320, 300, 300, 288, 288, 288, 270, 270, 256, 250, 240, 240, 240, 225, 216, 216, 216, 200, 192, 192, 180, 180, 180, 160, 150, 144, 144, 135, 125, 120, 120, 108, 100, 96, 90, 81, 75, 72, 72, 64, 60, 50, 45, 40, 36, 25, 18];

fn gauss_first_guess(resolution: usize) -> Vec<f64> {
    let gvals: [f64; 50] = [
        2.4048255577e0,
        5.5200781103e0,
        8.6537279129e0,
        11.7915344391e0,
        14.9309177086e0,
        18.0710639679e0,
        21.2116366299e0,
        24.3524715308e0,
        27.4934791320e0,
        30.6346064684e0,
        33.7758202136e0,
        36.9170983537e0,
        40.0584257646e0,
        43.1997917132e0,
        46.3411883717e0,
        49.4826098974e0,
        52.6240518411e0,
        55.7655107550e0,
        58.9069839261e0,
        62.0484691902e0,
        65.1899648002e0,
        68.3314693299e0,
        71.4729816036e0,
        74.6145006437e0,
        77.7560256304e0,
        80.8975558711e0,
        84.0390907769e0,
        87.1806298436e0,
        90.3221726372e0,
        93.4637187819e0,
        96.6052679510e0,
        99.7468198587e0,
        102.8883742542e0,
        106.0299309165e0,
        109.1714896498e0,
        112.3130502805e0,
        115.4546126537e0,
        118.5961766309e0,
        121.7377420880e0,
        124.8793089132e0,
        128.0208770059e0,
        131.1624462752e0,
        134.3040166383e0,
        137.4455880203e0,
        140.5871603528e0,
        143.7287335737e0,
        146.8703076258e0,
        150.0118824570e0,
        153.1534580192e0,
        156.2950342685e0,
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
    let mut new_vals = vec![0.0f64; nval];

    let denom = (((nval as f64 + 0.5).powi(2)) + convval).sqrt();

    for jval in 0..resolution {
        let mut root = (vals[jval] / denom).cos();
        let mut conv: f64 = 1.0;

        while conv.abs() >= precision {
            let mut mem2 = 1.0f64;
            let mut mem1 = root;
            let mut legfonc = 0.0f64;

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

#[pyclass]
pub struct ReducedGaussianGridMapper {
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
    pub cached_first_axis_vals: Vec<f64>,
}

#[pymethods]
impl ReducedGaussianGridMapper {
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
                let first = *map.get(&mapped_axes[0]).unwrap_or(&true);
                let second = *map.get(&mapped_axes[1]).unwrap_or(&false);
                (first, second)
            }
            None => (true, false),
        };

        if axis_reversed_second {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "ReducedGaussianGridMapper with second axis in decreasing order is not supported",
            ));
        }
        if !axis_resolved_first_ok(axis_reversed_first) {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "ReducedGaussianGridMapper with first axis in increasing order is not supported",
            ));
        }

        // Pre-compute first axis vals
        let computed = if resolution == 320 {
            REDUCED_GAUSSIAN_N320_LATS.to_vec()
        } else {
            compute_gauss_lats(resolution)
        };

        // Python: lats = lats[::-1] for N320 (reversed), and the gauss computation
        // produces ascending values (index 0 = positive/north pole end), then
        // new_vals[nval-1-jval] = -new_vals[jval], so index 0 is most positive.
        // The Python class stores them descending (north to south) since axis_reversed[first]=True.
        // REDUCED_GAUSSIAN_N320_LATS already stored in correct descending order (see data file).
        // For computed: new_vals[0] = asin_root (positive), new_vals[nval-1] = negative.
        // So computed is already descending.

        let md5 = md5_hash.or_else(|| {
            if resolution == 320 {
                Some("00c7b107673deb45f968637b661ea25b".to_string())
            } else {
                None
            }
        });

        Ok(ReducedGaussianGridMapper {
            base_axis,
            mapped_axes,
            resolution,
            md5_hash: md5,
            axis_reversed_first,
            axis_reversed_second,
            cached_first_axis_vals: computed,
        })
    }

    pub fn first_axis_vals(&self) -> Vec<f64> {
        self.cached_first_axis_vals.clone()
    }

    /// Returns latitude values that fall within [lower, upper].
    /// The axis is stored descending (north→south), so we find the window.
    pub fn map_first_axis(&self, lower: f64, upper: f64) -> Vec<f64> {
        // axis is descending; values in [lower, upper]
        self.cached_first_axis_vals
            .iter()
            .copied()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn second_axis_vals(&self, first_val: Vec<f64>) -> Vec<f64> {
        let tol = 1e-8;
        let fv = first_val[0];
        let first_idx = self
            .cached_first_axis_vals
            .iter()
            .position(|&v| (v - fv).abs() <= tol)
            .unwrap_or(0);
        let n_lons = self.lon_spacing_for_idx(first_idx) as usize;
        let second_spacing = 360.0 / n_lons as f64;
        (0..n_lons).map(|i| i as f64 * second_spacing).collect()
    }

    pub fn map_second_axis(&self, first_val: Vec<f64>, lower: f64, upper: f64) -> Vec<f64> {
        self.second_axis_vals(first_val)
            .into_iter()
            .filter(|&v| v >= lower && v <= upper)
            .collect()
    }

    pub fn find_second_idx(&self, first_val: Vec<f64>, second_val: f64) -> usize {
        let tol = 1e-8;
        let vals = self.second_axis_vals(first_val);
        vals.iter()
            .position(|&v| (v - second_val).abs() <= tol)
            .unwrap_or_else(|| vals.partition_point(|&x| x < second_val - tol))
    }

    pub fn unmap_first_val_to_start_line_idx(&self, first_val: f64) -> usize {
        let tol = 1e-8;
        let first_idx = self
            .cached_first_axis_vals
            .iter()
            .position(|&v| (v - first_val).abs() <= tol)
            .unwrap_or(0);
        // sum of lon_spacing for all rows before first_idx
        let spacing = self.lon_spacing_vec();
        spacing[..first_idx].iter().map(|&n| n as usize).sum()
    }

    #[pyo3(signature = (first_val, second_vals, _unmapped_idx=None))]
    pub fn unmap(&self, first_val: Vec<f64>, second_vals: Vec<f64>, _unmapped_idx: Option<Vec<usize>>) -> Vec<usize> {
        let tol = 1e-8;
        let fv = first_val[0];
        let first_idx = self
            .cached_first_axis_vals
            .iter()
            .position(|&v| (v - fv).abs() <= tol)
            .unwrap_or(0);

        let second_axis = self.second_axis_vals(first_val);
        let spacing = self.lon_spacing_vec();
        let prefix_sum: usize = spacing[..first_idx].iter().map(|&n| n as usize).sum();

        second_vals
            .iter()
            .map(|&sv| {
                let second_idx = second_axis
                    .iter()
                    .position(|&v| (v - sv).abs() <= tol)
                    .unwrap_or_else(|| second_axis.partition_point(|&x| x < sv - tol));
                prefix_sum + second_idx
            })
            .collect()
    }
}

impl ReducedGaussianGridMapper {
    fn lon_spacing_vec(&self) -> Vec<u32> {
        if self.resolution == 320 {
            LON_SPACING_N320.to_vec()
        } else {
            // For non-N320 resolutions, generate a symmetric spacing.
            // Standard reduced Gaussian: each row i (0-indexed from south pole)
            // has floor(4*i + 20) lon points, capped at 4*resolution.
            // Since we don't have precomputed data for other resolutions,
            // use a simple linear interpolation mirroring octahedral approach:
            // For a standard reduced Gaussian N grid, the number of points per
            // latitude increases from ~20 at poles to 4*N at equator.
            // This is an approximation; N320 uses the precomputed table above.
            let nrows = self.resolution * 2;
            let max_lons = 4 * self.resolution;
            (0..nrows)
                .map(|i| {
                    let j = if i < self.resolution { i } else { nrows - 1 - i };
                    let frac = j as f64 / (self.resolution as f64 - 1.0);
                    let n = (20.0 + frac * (max_lons as f64 - 20.0)).round() as u32;
                    n.max(1)
                })
                .collect()
        }
    }

    fn lon_spacing_for_idx(&self, idx: usize) -> u32 {
        if self.resolution == 320 {
            LON_SPACING_N320[idx]
        } else {
            let v = self.lon_spacing_vec();
            v[idx]
        }
    }
}

// Helper: first axis reversed (descending) is the only supported mode.
// Returns true if the axis_reversed_first value is acceptable (must be true).
fn axis_resolved_first_ok(reversed: bool) -> bool {
    reversed
}
