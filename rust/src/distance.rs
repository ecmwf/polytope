pub fn dist2(a: (f64, f64), b: (f64, f64)) -> f64 {
    let dx = a.0 - b.0;
    let dy = a.1 - b.1;
    dx * dx + dy * dy
}

pub fn box_dist2(center: (f64, f64), size: (f64, f64), point: (f64, f64)) -> f64 {
    // `size` is already the half-extent of each axis
    let min_x = center.0 - size.0;
    let max_x = center.0 + size.0;
    let min_y = center.1 - size.1;
    let max_y = center.1 + size.1;

    let dx = if point.0 < min_x {
        min_x - point.0
    } else if point.0 > max_x {
        point.0 - max_x
    } else {
        0.0
    };

    let dy = if point.1 < min_y {
        min_y - point.1
    } else if point.1 > max_y {
        point.1 - max_y
    } else {
        0.0
    };

    dx * dx + dy * dy
}