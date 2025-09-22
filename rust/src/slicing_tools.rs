use std::error::Error;
use geo::{LineString, Polygon, point, ConvexHull, CoordsIter};
use std::fmt;

pub fn is_contained_in(point: [f64; 2], polygon_points: &[[f64; 2]]) -> bool {
    let (min_y, max_y) = _slice_2D_vertical_extents(polygon_points, point[0]);
    point[1] >= min_y && point[1] <= max_y
}

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
            if (slice_axis_idx == 0 && a[0] == b[0])
                || (slice_axis_idx == 1 && a[1] == b[1])
            {
                intersects.push(b);
                continue;
            }

            let denom = if slice_axis_idx == 0 { a[0] - b[0] } else { a[1] - b[1] };
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
    [
        b[0] + t * (a[0] - b[0]),
        b[1] + t * (a[1] - b[1]),
    ]
}


fn polygon_extents(polytope_points: &Vec<[f64;2]>, slice_axis_idx: usize) -> (f64, f64){
    let (min_val, max_val) = polytope_points.into_iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY),
        |(min, max), polytope_point| {
            let value = if slice_axis_idx == 0 { polytope_point[0] } else { polytope_point[1] }; // Select the correct axis
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