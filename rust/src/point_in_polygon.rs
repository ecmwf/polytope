use geo::{polygon, Point, Contains, LineString, Polygon};

use pyo3::prelude::*;

#[pyfunction]
pub fn extract_point_in_poly(
    points: Vec<(f64, f64)>,
    poly: Vec<(f64, f64)>
) -> PyResult<Vec<(f64, f64)>> {
    let poly = {
        let mut poly = poly;
        if let Some(first) = poly.first() {
            if Some(first) != poly.last() {
                poly.push(*first);
            }
        }
        Polygon::new(LineString::from(poly), vec![])
    };

    let inside: Vec<(f64, f64)> = points
        .into_iter()
        .filter(|&(x, y)| {
            let pt = Point::new(x, y);
            poly.contains(&pt)
        })
        .collect();

    Ok(inside)
}

fn close_polygon(mut points: Vec<(f64, f64)>) -> Vec<(f64, f64)> {
    if let Some(first) = points.first() {
        if let Some(last) = points.last() {
            if first != last {
                points.push(*first);
            }
        }
    }
    points
}


fn find_bounds(points: &Vec<(f64, f64)>) -> Option<((f64, f64), (f64, f64))> {
    if points.is_empty() {
        return None;
    }

    let (min_x, max_x, min_y, max_y) = points.iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY, f64::INFINITY, f64::NEG_INFINITY),
        |(min_x, max_x, min_y, max_y), &(x, y)| {
            (
                min_x.min(x),
                max_x.max(x),
                min_y.min(y),
                max_y.max(y),
            )
        },
    );

    Some(((min_x, min_y), (max_x, max_y)))
}


#[pyfunction]
pub fn extract_point_in_poly_bbox(
    points: Vec<(f64, f64)>,
    poly: Vec<(f64, f64)>
) -> PyResult<Vec<(f64, f64)>> {
    let poly_bbox_option = find_bounds(&poly);
    let poly = {
        let mut poly = poly;
        if let Some(first) = poly.first() {
            if Some(first) != poly.last() {
                poly.push(*first);
            }
        }
        Polygon::new(LineString::from(poly), vec![])
    };

    if let Some(poly_bbox) = poly_bbox_option {
        let inside_bbox: Vec<(f64, f64)> = points.into_iter()
            .filter(|&(x, y)| {
                let ((min_x, min_y), (max_x, max_y)) = poly_bbox;
                min_x <= x && x <= max_x && min_y <= y && y <= max_y
            })
            .collect();

        let inside: Vec<(f64, f64)> = inside_bbox
            .into_iter()
            .filter(|&(x, y)| {
                let pt = Point::new(x, y);
                poly.contains(&pt)
            })
            .collect();

        return Ok(inside);
    }

    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
        "Polygon has no points, cannot compute bounding box.",
    ))
}

// fn main() {
//     // Create a polygon from raw coordinates
//     let poly = polygon![
//         (x: 0.0, y: 0.0),
//         (x: 5.0, y: 0.0),
//         (x: 5.0, y: 5.0),
//         (x: 0.0, y: 5.0),
//         (x: 0.0, y: 0.0), // must be closed
//     ];

//     let point = Point::new(3.0, 3.0);
//     println!("Point in polygon? {}", poly.contains(&point)); // true
// }