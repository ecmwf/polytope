/// Internal Rust trait for grid mappers.
/// Not exposed to Python (PyO3 doesn't support trait objects as pyclass).
pub trait GridMapper {
    /// Returns the values along the first axis.
    fn first_axis_vals(&self) -> Vec<f64>;

    /// Maps a value on the first axis to an index.
    fn map_first_axis(&self, val: f64) -> Option<usize>;

    /// Returns the values along the second axis for a given first-axis index.
    fn second_axis_vals(&self, first_idx: usize) -> Vec<f64>;

    /// Maps a value on the second axis (given the first-axis index) to an index.
    fn map_second_axis(&self, first_idx: usize, val: f64) -> Option<usize>;

    /// Finds the index on the second axis for a given first-axis index and value.
    fn find_second_idx(&self, first_idx: usize, val: f64) -> Option<usize>;

    /// Unmaps a first-axis value to the starting line index.
    fn unmap_first_val_to_start_line_idx(&self, val: f64) -> Option<usize>;

    /// Unmaps a flat grid index to (first_axis_val, second_axis_val).
    fn unmap(&self, flat_idx: usize) -> Option<(f64, f64)>;
}

pub mod data;

// Upcoming submodules (files to be created):
pub mod regular;
pub mod octahedral;
pub mod reduced_gaussian;
pub mod healpix;
pub mod healpix_nested;
pub mod reduced_ll;
pub mod local_regular;
pub mod unstructured;
pub mod lambert_conformal;
pub mod irregular;
