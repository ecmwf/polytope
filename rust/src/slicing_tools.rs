use geo::{point, ConvexHull, CoordsIter, LineString, Polygon};
use pyo3::prelude::*;
use std::error::Error;
use std::fmt;

// ---------------------------------------------------------------------------
// N-dimensional generalised slice
// ---------------------------------------------------------------------------

/// Linearly interpolate between two N-dimensional points.
fn lerp_nd(a: &[f64], b: &[f64], t: f64) -> Vec<f64> {
    a.iter()
        .zip(b.iter())
        .map(|(&ai, &bi)| bi + t * (ai - bi))
        .collect()
}

/// Find all intersection points of the hyperplane `points[slice_axis_idx] == value`
/// with the convex polytope defined by `polytope_points` (N-D, N >= 1).
/// Works exactly like the Python `_find_intersects` but for arbitrary dimension.
fn find_intersects_nd(
    polytope_points: &[Vec<f64>],
    slice_axis_idx: usize,
    value: f64,
) -> Vec<Vec<f64>> {
    let mut intersects = Vec::new();

    let above: Vec<&Vec<f64>> = polytope_points
        .iter()
        .filter(|p| p[slice_axis_idx] >= value)
        .collect();
    let below: Vec<&Vec<f64>> = polytope_points
        .iter()
        .filter(|p| p[slice_axis_idx] <= value)
        .collect();

    for a in &above {
        for b in &below {
            if (a[slice_axis_idx] - b[slice_axis_idx]).abs() < f64::EPSILON {
                // Edge lies on the slice plane — keep b
                intersects.push((*b).clone());
                continue;
            }
            let t = (value - b[slice_axis_idx]) / (a[slice_axis_idx] - b[slice_axis_idx]);
            intersects.push(lerp_nd(a, b, t));
        }
    }
    intersects
}

/// Remove the coordinate at `slice_axis_idx` from every point, reducing dimension by 1.
fn reduce_dimension(points: Vec<Vec<f64>>, slice_axis_idx: usize) -> Vec<Vec<f64>> {
    points
        .into_iter()
        .map(|p| {
            p.into_iter()
                .enumerate()
                .filter(|(i, _)| *i != slice_axis_idx)
                .map(|(_, v)| v)
                .collect()
        })
        .collect()
}

/// Compute the 2-D convex hull of `points` using the `geo` crate.
/// Returns the hull vertices (open ring — last != first).
fn convex_hull_2d(points: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let coords: Vec<[f64; 2]> = points.iter().map(|p| [p[0], p[1]]).collect();
    let hull_pts = find_qhull_points2(&coords);
    hull_pts.into_iter().map(|[x, y]| vec![x, y]).collect()
}

/// Compute the 1-D "hull" (just min and max) of `points`.
fn convex_hull_1d(points: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let min = points.iter().map(|p| p[0]).fold(f64::INFINITY, f64::min);
    let max = points
        .iter()
        .map(|p| p[0])
        .fold(f64::NEG_INFINITY, f64::max);
    if (min - max).abs() < f64::EPSILON {
        vec![vec![min]]
    } else {
        vec![vec![min], vec![max]]
    }
}

/// Python-callable N-dimensional slice.
///
/// `polytope_points` : list of N-dimensional points (list[list[float]])
/// `is_flat`         : whether the polytope is degenerate / flat (mirrors Python's ConvexPolytope.is_flat)
/// `value`           : the value at which to slice along `slice_axis_idx`
/// `slice_axis_idx`  : which dimension to slice along
///
/// Returns `None` when there is no intersection, otherwise the reduced polytope
/// as `list[list[float]]`.
#[pyfunction]
pub fn slice_polytope(
    polytope_points: Vec<Vec<f64>>,
    is_flat: bool,
    value: f64,
    slice_axis_idx: usize,
) -> PyResult<Option<Vec<Vec<f64>>>> {
    // Mirror the `is_flat` fast-path from Python's `slice()`
    if is_flat {
        let hit = polytope_points
            .iter()
            .any(|p| p.iter().any(|&v| (v - value).abs() < f64::EPSILON));
        if hit {
            return Ok(Some(vec![vec![value]]));
        } else {
            return Ok(None);
        }
    }

    let intersects = find_intersects_nd(&polytope_points, slice_axis_idx, value);

    if intersects.is_empty() {
        return Ok(None);
    }

    // Reduce dimension
    let reduced = reduce_dimension(intersects, slice_axis_idx);
    let ndim = reduced[0].len();

    // Mirror Python: if fewer points than ndim+1, no hull needed
    if reduced.len() < ndim + 1 {
        return Ok(Some(reduced));
    }

    // Compute hull based on dimension of the reduced points
    let hull = match ndim {
        0 => return Ok(None),
        1 => convex_hull_1d(&reduced),
        2 => convex_hull_2d(&reduced),
        _ => {
            // For >2D we cannot easily compute an exact convex hull here without
            // an N-D library. Return all reduced intersection points; the caller
            // can further prune if needed. In practice polytope-python rarely
            // exceeds 2D after the first few slice steps, so this is fine.
            reduced
        }
    };

    Ok(Some(hull))
}

pub fn is_contained_in(point: [f64; 2], polygon_points: &[[f64; 2]]) -> bool {
    let (min_y, max_y) = _slice_2D_vertical_extents(polygon_points, point[0]);
    point[1] >= min_y && point[1] <= max_y
}

#[allow(non_snake_case)]
fn _slice_2D_vertical_extents(polygon_points: &[[f64; 2]], val: f64) -> (f64, f64) {
    let intersects = _find_intersects(polygon_points, 0, val);
    intersects.iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY),
        |(min, max), &[_x, y]| (min.min(y), max.max(y)),
    )
}

// Restricted to 2D points for now
fn _find_intersects(
    polytope_points: &[[f64; 2]],
    slice_axis_idx: usize,
    value: f64,
) -> Vec<[f64; 2]> {
    let mut intersects = Vec::new();

    let is_above = |point: &&[f64; 2]| point[slice_axis_idx] >= value;
    let is_below = |point: &&[f64; 2]| point[slice_axis_idx] <= value;

    for &a in polytope_points.iter().filter(is_above) {
        for &b in polytope_points.iter().filter(is_below) {
            // Skip duplicate incident case
            if a == b {
                continue;
            }

            // Edge is incident with the slice plane
            if (slice_axis_idx == 0 && a[0] == b[0]) || (slice_axis_idx == 1 && a[1] == b[1]) {
                intersects.push(b);
                continue;
            }

            let denom = if slice_axis_idx == 0 {
                a[0] - b[0]
            } else {
                a[1] - b[1]
            };
            if denom.abs() < f64::EPSILON {
                continue; // avoid division by zero
            }

            let t = (value - if slice_axis_idx == 0 { b[0] } else { b[1] }) / denom;
            let intersect = lerp(a, b, t);
            intersects.push(intersect);
        }
    }

    intersects
}

fn lerp(a: [f64; 2], b: [f64; 2], t: f64) -> [f64; 2] {
    [b[0] + t * (a[0] - b[0]), b[1] + t * (a[1] - b[1])]
}

fn polygon_extents(polytope_points: &Vec<[f64; 2]>, slice_axis_idx: usize) -> (f64, f64) {
    let (min_val, max_val) = polytope_points.into_iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY),
        |(min, max), polytope_point| {
            let value = if slice_axis_idx == 0 {
                polytope_point[0]
            } else {
                polytope_point[1]
            }; // Select the correct axis
            (min.min(value), max.max(value))
        },
    );
    (min_val, max_val)
}

pub fn slice_in_two(
    polytope_points: Option<&Vec<[f64; 2]>>,
    value: f64,
    slice_axis_idx: usize,
) -> Result<(Option<Vec<[f64; 2]>>, Option<Vec<[f64; 2]>>), QhullError> {
    let polytope_points = match polytope_points {
        Some(p) if !p.is_empty() => p,
        _ => return Ok((None, None)),
    };

    // Calculate extents once
    let (x_lower, x_upper) = polygon_extents(polytope_points, slice_axis_idx);

    // Fast-path: no intersection with slicing plane
    if x_upper <= value {
        return Ok((Some(polytope_points.clone()), None));
    } else if value < x_lower {
        return Ok((None, Some(polytope_points.clone())));
    }

    // Only compute intersects when we *know* they’re needed
    let intersects = _find_intersects(polytope_points, slice_axis_idx, value);
    let mut left_points = Vec::with_capacity(polytope_points.len() + intersects.len());
    let mut right_points = Vec::with_capacity(polytope_points.len() + intersects.len());

    // Partition points
    for &point in polytope_points {
        if point[slice_axis_idx] <= value {
            left_points.push(point);
        } else {
            right_points.push(point);
        }
    }

    // Add intersecting points to both sides
    left_points.extend_from_slice(&intersects);
    right_points.extend_from_slice(&intersects);

    // Skip convex hull construction if one side has too few points
    let left_polygon = if left_points.len() >= 3 {
        find_qhull_points3(&left_points)?
    } else {
        None
    };

    let right_polygon = if right_points.len() >= 3 {
        find_qhull_points3(&right_points)?
    } else {
        None
    };

    Ok((left_polygon, right_polygon))
}

fn vec_to_polygon(coords: &Vec<[f64; 2]>) -> Polygon {
    let closed_coords = close_ring(coords);
    let linestring: LineString = closed_coords
        .into_iter()
        .map(|[x, y]| point!(x: x, y: y))
        .collect();
    Polygon::new(linestring, vec![])
}

fn close_ring(coords: &Vec<[f64; 2]>) -> Vec<[f64; 2]> {
    let mut closed = coords.clone();
    if let (Some(first), Some(last)) = (coords.first(), coords.last()) {
        if first != last {
            closed.push(*first);
        }
    }
    closed
}

fn find_qhull_points2(points: &Vec<[f64; 2]>) -> Vec<[f64; 2]> {
    let poly = vec_to_polygon(points);
    let hull = poly.convex_hull();

    // unique_points
    let exterior_coords = hull.exterior().coords_iter().collect::<Vec<_>>();

    // exterior_coords is closed, so remove the last point (duplicate of first)
    exterior_coords[..exterior_coords.len() - 1]
        .iter()
        .map(|c| [c.x, c.y])
        .collect()
}

fn find_qhull_points3(points: &Vec<[f64; 2]>) -> Result<Option<Vec<[f64; 2]>>, QhullError> {
    // If empty input, return None
    if points.is_empty() {
        return Ok(None);
    }

    // Use your hull function here
    let hull_points = find_qhull_points2(points);

    Ok(Some(hull_points))
}

#[derive(Debug)]
pub enum QhullError {
    FlatError,
    OtherError(String),
}

impl fmt::Display for QhullError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            QhullError::FlatError => write!(f, "QHull error: flat or invalid geometry"),
            QhullError::OtherError(msg) => write!(f, "QHull error: {}", msg),
        }
    }
}

impl Error for QhullError {}
