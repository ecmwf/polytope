#[pyfunction]
pub fn unmap_regular(
    resolution: usize,
    first_val: Vec<f64>,      // <-- now Vec<f64> passed by reference
    second_vals: Vec<f64>,     // <-- now Vec<f64> passed by reference
    axis_reversed: Vec<usize>
) -> PyResult<Vec<usize>> {
    let deg_increment = 90 / resolution;
    let tol = 1e-8;
    let first_axis = first_axis_vals_regular(deg_increment, axis_reversed);

    let first_val = *first_axis
        .iter()
        .find(|&&i| first_val - tol <= i && i <= first_val + tol)
        .expect("First value not found");

    let first_idx = first_axis
        .iter()
        .position(|&v| v == first_val)
        .unwrap();

    let second_axis = second_axis_vals(first_val, resolution, deg_increment);

    second_vals
        .iter()
        .map(|&second_val| {
            let val = *second_axis
                .iter()
                .find(|&&i| second_val - tol <= i && i <= second_val + tol)
                .expect("Second value not found");

            let second_idx = second_axis
                .iter()
                .position(|&v| v == val)
                .unwrap();

            axes_idx_to_regular_idx(first_idx, second_idx, resolution)
        })
        .collect()
}

pub fn first_axis_vals_regular(deg_increment: f64, resolution: usize, axis_reversed: Vec<usize>) -> Vec<f64> {
    let n = 2 * resolution;

    if axis_reversed[0] {
        (0..n)
            .map(|i| 90.0 - i as f64 * deg_increment)
            .collect()
    } else {
        (0..n)
            .map(|i| -90.0 + i as f64 * deg_increment)
            .collect()
    }
}


pub fn second_axis_vals(_first_val: f64, resolution: usize, deg_increment: f64) -> Vec<f64> {
    (0..4 * resolution)
        .map(|i| i as f64 * deg_increment)
        .collect()
}

pub fn axes_idx_to_regular_idx(first_idx: usize, second_idx: usize, resolution: usize) -> usize {
    first_idx * 4 * resolution + second_idx
}
