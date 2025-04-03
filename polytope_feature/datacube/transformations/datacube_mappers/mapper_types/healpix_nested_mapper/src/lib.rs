use pyo3::prelude::*;

// #[pyfunction]
// fn axes_idx_to_healpix_idx_batch(
//     resolution: usize,
//     first_idxs: Vec<usize>,
//     second_idxs: Vec<usize>,
// ) -> Vec<usize> {
//     let mut results = Vec::with_capacity(second_idxs.len());

//     for (&first_idx, &second_idx) in first_idxs.iter().zip(second_idxs.iter()) {
//         let mut idx = 0;

//         // First loop
//         for i in 0..(resolution - 1) {
//             if i != first_idx {
//                 idx += 4 * (i + 1);
//             } else {
//                 idx += second_idx;
//                 results.push(idx);
//                 break;  // Exit loop when match is found
//             }
//         }

//         // Second loop
//         for i in (resolution - 1)..(3 * resolution) {
//             if i != first_idx {
//                 idx += 4 * resolution;
//             } else {
//                 idx += second_idx;
//                 results.push(idx);
//                 break;
//             }
//         }

//         // Third loop
//         for i in (3 * resolution)..(4 * resolution - 1) {
//             if i != first_idx {
//                 idx += 4 * (4 * resolution - 1 - i);
//             } else {
//                 idx += second_idx;
//                 results.push(idx);
//                 break;
//             }
//         }
//     }

//     results
// }

#[pyfunction]
fn axes_idx_to_healpix_idx_batch(
    resolution: usize,
    first_idx: usize,
    second_idxs: Vec<usize>,
) -> Vec<usize> {
    let mut results = Vec::with_capacity(second_idxs.len());

    for &second_idx in second_idxs.iter() {
        results.push(axes_idx_to_healpix_idx(resolution, first_idx, second_idx));
    }

    results
}

fn axes_idx_to_healpix_idx(resolution: usize, first_idx: usize, second_idx: usize) -> usize {
    let mut idx = 0;

    for i in 0..(resolution - 1) {
        if i != first_idx {
            idx += 4 * (i + 1);
        } else {
            idx += second_idx;
            return idx;
        }
    }

    for i in (resolution - 1)..(3 * resolution) {
        if i != first_idx {
            idx += 4 * resolution;
        } else {
            idx += second_idx;
            return idx;
        }
    }

    for i in (3 * resolution)..(4 * resolution - 1) {
        if i != first_idx {
            idx += 4 * (4 * resolution - 1 - i);
        } else {
            idx += second_idx;
            return idx;
        }
    }

    idx // Return idx in case no match is found
}


use std::f64;

/// Fast integer square root
// fn int_sqrt(i: usize) -> usize {
//     (i as f64 + 0.5).sqrt() as usize
// }

// /// div_03 function (bitwise optimized division)
// fn div_03(a: usize, b: usize) -> usize {
//     let t = if a >= (b << 1) { 1 } else { 0 };
//     let a = a - t * (b << 1);
//     (t << 1) + (if a >= b { 1 } else { 0 })
// }

// /// pll function (precomputed array)
// fn pll(f: usize) -> usize {
//     let pll_values = [1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7];
//     pll_values[f]
// }

// /// nest_encode_bits (efficient bit interleaving)
// fn nest_encode_bits(mut i: usize) -> usize {
//     let masks = [
//         0x00000000FFFFFFFF,
//         0x0000FFFF0000FFFF,
//         0x00FF00FF00FF00FF,
//         0x0F0F0F0F0F0F0F0F,
//         0x3333333333333333,
//         0x5555555555555555,
//     ];

//     let mut b = i & masks[0];

//     b = (b ^ (b << 16)) & masks[1];
//     b = (b ^ (b << 8)) & masks[2];
//     b = (b ^ (b << 4)) & masks[3];
//     b = (b ^ (b << 2)) & masks[4];
//     b = (b ^ (b << 1)) & masks[5];
//     b
// }

// /// fij_to_nest function
// fn fij_to_nest(f: usize, i: usize, j: usize, k: usize) -> usize {
//     (f << (2 * k)) + nest_encode_bits(i) + (nest_encode_bits(j) << 1)
// }

// /// Converts ring index to nested index
// fn ring_to_nested(idx: usize, nside: usize, npix: usize, ncap: usize, k: usize) -> usize {
//     if idx < ncap {
//         // North polar cap
//         let nring = (1 + int_sqrt(2 * idx + 1)) >> 1;
//         let phi = 1 + idx - 2 * nring * (nring - 1);
//         let f = div_03(phi - 1, nring);
//         return to_nest(f, nring, nring, phi, 0, k, nside);
//     }

//     if npix - ncap <= idx {
//         // South polar cap
//         let nring = (1 + int_sqrt(2 * npix - 2 * idx - 1)) >> 1;
//         let phi = 1 + idx + 2 * nring * (nring - 1) + 4 * nring - npix;
//         let ring = 4 * nside - nring;
//         let f = div_03(phi - 1, nring) + 8;
//         return to_nest(f, ring, nring, phi, 0, k, nside);
//     }


//     println!("ARE IN MIDDLE???");
//     // Equatorial belt
//     let ip = idx - ncap;
//     let tmp = ip >> (k + 2);
//     let phi = ip - tmp * 4 * nside + 1;
//     let ring = tmp + nside;

//     let ifm = 1 + ((phi - 1 - ((1 + tmp) >> 1)) >> k);
//     let ifp = 1 + ((phi - 1 - ((1 - tmp + 2 * nside) >> 1)) >> k);
//     let f = if ifp == ifm {
//         ifp | 4
//     } else if ifp < ifm {
//         ifp
//     } else {
//         ifm + 8
//     };

//     to_nest(f, ring, nside, phi, ring & 1, k, nside)
// }

// #[pyfunction]
// fn ring_to_nested_batched(idxs: Vec<usize>, nside: usize, npix: usize, ncap: usize, k: usize) -> Vec<usize> {
//     let mut results = Vec::with_capacity(idxs.len());
//     for &idx in idxs.iter() {
//         results.push(ring_to_nested(idx, nside, npix, ncap, k));
//     }
//     results
// }


// // /// Converts to nested index
// // fn to_nest(f: usize, ring: usize, nring: usize, phi: usize, shift: usize, k: usize, nside: usize) -> usize {
// //     let r = ((2 + (f >> 2)) << k) - ring - 1;
// //     let mut p = 2 * phi - pll(f) * nring - shift - 1;
    
// //     println!("INSIDE TO_NEST IN RUST");
// //     println!("{:?}", vec![phi, nring, shift, p]);

// //     if p >= 2 * nside {
// //         p -= 8 * nside;
// //     }

// //     let i = (r + p) >> 1;
// //     let j = (r - p) >> 1;

// //     fij_to_nest(f, i, j, k)
// // }

// fn to_nest(
//     f: usize, ring: usize, nring: usize, phi: usize, 
//     shift: usize, k: usize, nside: usize
// ) -> usize {
//     let r: isize = ((2 + (f >> 2)) << k) as isize - ring as isize - 1;
//     let mut p: isize = (2 * phi) as isize - pll(f) as isize * nring as isize - shift as isize - 1;

//     if p >= (2 * nside) as isize {
//         p -= (8 * nside) as isize;
//     }

//     let i: usize = ((r + p) >> 1) as usize;
//     let j: usize = ((r - p) >> 1) as usize;

//     fij_to_nest(f, i, j, k)
// }

fn int_sqrt(i: isize) -> isize {
    ((i as f64 + 0.5).sqrt()) as isize
}

/// div_03 function (bitwise optimized division)
fn div_03(a: isize, b: isize) -> isize {
    let t = if a >= (b << 1) { 1 } else { 0 };
    let a = a - t * (b << 1);
    (t << 1) + if a >= b { 1 } else { 0 }
}

/// pll function (precomputed array)
fn pll(f: usize) -> isize {
    let pll_values = [1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7];
    pll_values[f] as isize
}

/// nest_encode_bits (efficient bit interleaving)
fn nest_encode_bits(mut i: isize) -> isize {
    let masks = [
        0x00000000FFFFFFFF,
        0x0000FFFF0000FFFF,
        0x00FF00FF00FF00FF,
        0x0F0F0F0F0F0F0F0F,
        0x3333333333333333,
        0x5555555555555555,
    ];

    let mut b = i & masks[0];

    b = (b ^ (b << 16)) & masks[1];
    b = (b ^ (b << 8)) & masks[2];
    b = (b ^ (b << 4)) & masks[3];
    b = (b ^ (b << 2)) & masks[4];
    b = (b ^ (b << 1)) & masks[5];
    b
}

/// fij_to_nest function
fn fij_to_nest(f: usize, i: isize, j: isize, k: usize) -> usize {
    (f << (2 * k)) + nest_encode_bits(i) as usize + ((nest_encode_bits(j) as usize) << 1)
}

/// Converts ring index to nested index
fn ring_to_nested(idx: isize, nside: isize, npix: isize, ncap: isize, k: isize) -> usize {
    if idx < ncap {
        // North polar cap
        let nring = (1 + int_sqrt(2 * idx + 1)) >> 1;
        let phi = 1 + idx - 2 * nring * (nring - 1);
        let f = div_03(phi - 1, nring);
        return to_nest(f as usize, nring, nring, phi, 0, k, nside);
    }

    if npix - ncap <= idx {
        // South polar cap
        let nring = (1 + int_sqrt(2 * npix - 2 * idx - 1)) >> 1;
        let phi = 1 + idx + 2 * nring * (nring - 1) + 4 * nring - npix;
        let ring = 4 * nside - nring;
        let f = div_03(phi - 1, nring) + 8;
        return to_nest(f as usize, ring, nring, phi, 0, k, nside);
    }

    // Equatorial belt
    let ip = idx - ncap;
    let tmp = ip >> (k + 2);
    let phi = ip - tmp * 4 * nside + 1;
    let ring = tmp + nside;

    let ifm = 1 + ((phi - 1 - ((1 + tmp) >> 1)) >> k);
    let ifp = 1 + ((phi - 1 - ((1 - tmp + 2 * nside) >> 1)) >> k);
    let f = if ifp == ifm {
        ifp | 4
    } else if ifp < ifm {
        ifp
    } else {
        ifm + 8
    };

    to_nest(f as usize, ring, nside, phi, ring & 1, k, nside)
}

#[pyfunction]
fn ring_to_nested_batched(idxs: Vec<isize>, nside: isize, npix: isize, ncap: isize, k: isize) -> Vec<usize> {
    let mut results = Vec::with_capacity(idxs.len());
    for &idx in idxs.iter() {
        results.push(ring_to_nested(idx, nside, npix, ncap, k));
    }
    results
}

/// Converts to nested index
fn to_nest(
    f: usize, ring: isize, nring: isize, phi: isize, 
    shift: isize, k: isize, nside: isize
) -> usize {
    let r: isize = ((2 + (f >> 2)) << k) as isize - ring - 1;
    let mut p: isize = (2 * phi) - pll(f) * nring - shift - 1;

    if p >= (2 * nside) {
        p -= (8 * nside);
    }

    let i = (r + p) >> 1;
    let j = (r - p) >> 1;

    fij_to_nest(f, i, j, k as usize)
}

// fn first_axis_vals(resolution: usize) {

// }

// def first_axis_vals(self):
//         rad2deg = 180 / math.pi
//         vals = [0] * (4 * self._resolution - 1)

//         # Polar caps
//         for i in range(1, self._resolution):
//             val = 90 - (rad2deg * math.acos(1 - (i * i / (3 * self._resolution * self._resolution))))
//             vals[i - 1] = val
//             vals[4 * self._resolution - 1 - i] = -val
//         # Equatorial belts
//         for i in range(self._resolution, 2 * self._resolution):
//             val = 90 - (rad2deg * math.acos((4 * self._resolution - 2 * i) / (3 * self._resolution)))
//             vals[i - 1] = val
//             vals[4 * self._resolution - 1 - i] = -val
//         # Equator
//         vals[2 * self._resolution - 1] = 0
//         return vals



#[pymodule]
fn healpix_nested_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(axes_idx_to_healpix_idx_batch, m)?)?;
    m.add_function(wrap_pyfunction!(ring_to_nested_batched, m)?)?;
    Ok(())
}
