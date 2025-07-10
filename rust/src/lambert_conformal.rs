use std::f64::consts::{PI, FRAC_PI_2};

use pyo3::prelude::*;

fn normalise_longitude_in_degrees(mut lon: f64) -> f64 {
    while lon < 0.0 {
        lon += 360.0;
    }
    while lon > 360.0 {
        lon -= 360.0;
    }
    lon
}

fn adjust_lon_radians(mut lon: f64) -> f64 {
    if lon > PI {
        lon -= 2.0 * PI;
    }
    if lon < -PI {
        lon += 2.0 * PI;
    }
    lon
}

fn compute_phi(eccent: f64, ts: f64) -> f64 {
    let max_iter = 15;
    let eccnth = 0.5 * eccent;
    let mut phi = FRAC_PI_2 - 2.0 * ts.atan();

    for _ in 0..=max_iter {
        let sinpi = phi.sin();
        let con = eccent * sinpi;
        let dphi = FRAC_PI_2 - 2.0 * (ts * (((1.0 - con) / (1.0 + con)).powf(eccnth))).atan() - phi;
        phi += dphi;
        if dphi.abs() <= 1e-10 {
            return phi;
        }
    }

    0.0
}

fn compute_m(eccent: f64, sinphi: f64, cosphi: f64) -> f64 {
    let con = eccent * sinphi;
    cosphi / (1.0 - con * con).sqrt()
}

fn compute_t(eccent: f64, phi: f64, sinphi: f64) -> f64 {
    let con = eccent * sinphi;
    let com = 0.5 * eccent;
    let pow = ((1.0 - con) / (1.0 + con)).powf(com);
    (0.5 * (FRAC_PI_2 - phi)).tan() / pow
}

fn calculate_eccentricity(minor: f64, major: f64) -> f64 {
    let temp = minor / major;
    (1.0 - temp * temp).sqrt()
}

fn xy2lonlat(
    radius: f64,
    n: f64,
    f: f64,
    rho0_bare: f64,
    lov_in_radians: f64,
    mut x: f64,
    mut y: f64,
) -> (f64, f64) {
    x /= radius;
    y = rho0_bare - y / radius;
    let mut rho = (x * x + y * y).sqrt();
    let rad2deg = 180.0 / PI;

    if rho != 0.0 {
        if n < 0.0 {
            rho = -rho;
            x = -x;
            y = -y;
        }

        let lat_radians = 2.0 * (f / rho).powf(1.0 / n).atan() - FRAC_PI_2;
        let lon_radians = x.atan2(y) / n;
        let lon_deg = (lon_radians + lov_in_radians) * rad2deg;
        let lat_deg = lat_radians * rad2deg;
        (lon_deg, lat_deg)
    } else {
        let lat_sign = if n > 0.0 { FRAC_PI_2 } else { -FRAC_PI_2 };
        (0.0, lat_sign * rad2deg)
    }
}

#[pyfunction]
pub fn get_latlons_sphere(latin1inradians: f64, latin2inradians: f64, radius: f64, latfirstinradians: f64, ladinradians: f64,
lonfirstinradians: f64, lovinradians: f64, ny: i32, nx: i32, dy: f64, dx: f64) -> PyResult<Vec<[f64; 2]>> {
    let n = if (latin1inradians - latin2inradians).abs() < 1e-9 {
        latin1inradians.sin()
    } else {
        let num = (latin1inradians.cos() / latin2inradians.cos()).ln();
         let denom = ((PI / 4.0 + latin2inradians / 2.0).tan()
            / (PI / 4.0 + latin1inradians / 2.0).tan())
            .ln();
        num / denom
    };
    let f = (latin1inradians.cos()
        * (PI / 4.0 + latin1inradians / 2.0).tan().powf(n))
        / n;
    let rho = radius
        * f
        * (PI / 4.0 + latfirstinradians / 2.0).tan().powf(-n);
    let rho0_bare = f * (PI / 4.0 + ladinradians / 2.0).tan().powf(-n);
    let rho0 = radius * rho0_bare;
    let mut lon_diff = lonfirstinradians - lovinradians;
    if lon_diff > PI {
        lon_diff -= 2.0 * PI;
    }
    if lon_diff < -PI {
        lon_diff += 2.0 * PI;
    }
    let angle = n * lon_diff;
    let x0 = rho * angle.sin();
    let y0 = rho0 - rho * angle.cos();

    let mut coords = Vec::new();
    for j in 0..ny {
        let y = y0 + (j as f64) * dy;
        for i in 0..nx {
            let x = x0 + (i as f64) * dx;
            let (mut lon_deg, lat_deg) =
                xy2lonlat(radius, n, f, rho0_bare, lovinradians, x, y);
            lon_deg = normalise_longitude_in_degrees(lon_deg);
            coords.push([lat_deg, lon_deg]);
        }
    }
    Ok(coords)
}

#[pyfunction]
pub fn get_latlons_oblate(latin1inradians: f64, latin2inradians: f64, earthminoraxisinmetres: f64, earthmajoraxisinmetres: f64,
latfirstinradians: f64, ladinradians: f64,
lonfirstinradians: f64, lovinradians: f64, ny: i32, nx: i32, dy: f64, dx: f64) -> Vec<[f64; 2]> {
    let e = calculate_eccentricity(earthminoraxisinmetres, earthmajoraxisinmetres);
    let mut sin_po = latin1inradians.sin();
    let mut cos_po = latin1inradians.cos();
    let con = sin_po;
    let ms1 = compute_m(e, sin_po, cos_po);
    let ts1 = compute_t(e, latin1inradians, sin_po);
    sin_po = latin2inradians.sin();
    cos_po = latin2inradians.cos();
    let ms2 = compute_m(e, sin_po, cos_po);
    let ts2 = compute_t(e, latin2inradians, sin_po);
    sin_po = ladinradians.sin();
    let ts0 = compute_t(e, ladinradians, sin_po);
    let ns = if (latin1inradians - latin2inradians).abs() > 1e-10 {
        (ms1 / ms2).ln() / (ts1 / ts2).ln()
    } else {
        con
    };
    let f_cst = ms1 / (ns * ts1.powf(ns));
    let rh = earthmajoraxisinmetres * f_cst * ts0.powf(ns);
    let con_lat_diff = (latfirstinradians.abs() - FRAC_PI_2).abs();
    let (rh1, theta) = if con_lat_diff > 1e-10 {
        let sinphi = latfirstinradians.sin();
        let ts = compute_t(e, latfirstinradians, sinphi);
        let rh1 = earthmajoraxisinmetres * f_cst * ts.powf(ns);
        let theta = ns * adjust_lon_radians(lonfirstinradians - lovinradians);
        (rh1, theta)
    } else {
        let con = latfirstinradians * ns;
        (0.0, con)
    };
    let x0 = -rh1 * theta.sin();
    let y0 = -(rh - rh1 * theta.cos());
    let false_easting = x0;
    let false_northing = y0;
    let mut coords = Vec::new();
    let rad2deg = 180.0 / PI;
    for j in 0..ny {
        let y = (j as f64) * dy;
        for i in 0..nx {
            let x = (i as f64) * dx;
            let dx_ = x - false_easting;
            let dy_ = rh - y + false_northing;
            let mut rh1 = (dx_ * dx_ + dy_ * dy_).sqrt();
            let mut con = 1.0;
            if ns <= 0.0 {
                rh1 = -rh1;
                con = -1.0;
            }
            let mut theta = 0.0;
            if rh1 != 0.0 {
                theta = (con * dx_).atan2(con * dy_);
            }
            let lat_rad = if rh1 != 0.0 || ns > 0.0 {
                let con = 1.0 / ns;
                let ts = (rh1 / (earthmajoraxisinmetres * f_cst)).powf(con);
                compute_phi(e, ts)
            } else {
                -FRAC_PI_2
            };
            let lon_rad = adjust_lon_radians(theta / ns + lovinradians);
            let lat_deg = lat_rad * rad2deg;
            let lon_deg = normalise_longitude_in_degrees(lon_rad * rad2deg);
            coords.push([lat_deg, lon_deg]);
        }
    }
    coords
}

