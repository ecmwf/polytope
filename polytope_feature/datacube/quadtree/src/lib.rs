#![allow(dead_code)]

use pyo3::prelude::*;   // Do not use * for importing here

use std::sync::{Arc, Mutex};

use qhull::Qh;
use std::collections::HashSet;
use std::error::Error;
use pyo3::exceptions::PyRuntimeError;




// TODO: can we not replace this QuadPoint by just the index of the point in the list potentially?

// #[derive(Debug)]
// #[derive(Clone)]
// struct QuadPoint {
//     item: (f64, f64),
//     index: usize,
// }


// impl QuadPoint {
//     fn new(item: (f64, f64), index: usize) -> Self {
//         Self {item, index}
//     }

//     fn sizeof(&self) -> usize {
//         let size = size_of::<Self>();
//         size
//     }
// }

#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadTreeNode {
    // points: Option<Vec<QuadPoint>>,
    points: Option<Vec<usize>>,
    children: Vec<usize>,

    #[pyo3(get, set)]
    center: (f64, f64),
    size: (f64, f64),
    depth: i32,
}

impl QuadTreeNode {
    fn sizeof(&self) -> usize {
        let mut size = size_of::<Self>(); // Base struct size
        // Dynamically allocated memory for points
        if let Some(points) = &self.points {
            // let points_size: usize = points.capacity() * size_of::<usize>();
            let points_size: usize = points.len() * size_of::<usize>();
            size += points_size;
        }
        // Dynamically allocated memory for children
        let children_size = self.children.len() * size_of::<usize>();
        size += children_size;
        size
    }
}


#[derive(Debug)]
#[pyclass]
struct QuadTree {
    nodes: Vec<QuadTreeNode>,
}

#[pymethods]
impl QuadTree {
    #[new]
    fn new() -> Self {
        QuadTree {
            nodes: Vec::new(),
        }
    }

    fn sizeof(&self) -> usize {
        let mut size = size_of::<Self>(); // Base struct size (Vec metadata)
        // Memory allocated for `nodes` (Vec<QuadTreeNode>)
        let nodes_size: usize = self.nodes.len() * size_of::<QuadTreeNode>();
        size += nodes_size;
        // Sum sizes of each QuadTreeNode (including their allocated memory)
        for (i, node) in self.nodes.iter().enumerate() {
            let node_size = node.sizeof();
            size += node_size;
        }
        size
    }

    // /// Get the center of a node
    fn get_center(&self, index: usize) -> PyResult<(f64, f64)> {
        let nodes = &self.nodes;
        nodes.get(index).map(|n| n.center).ok_or_else(|| {
            pyo3::exceptions::PyIndexError::new_err("Invalid node index")
        })
    }


    fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
        self.create_node((0.0,0.0), (180.0, 90.0), 0);
        // points.into_iter().enumerate().for_each(|(index, p)| {
        //     self.insert(index, 0, &points);
        // });
        points.iter().enumerate().for_each(|(index, p)| {
            self.insert(index, 0, &points);
        });
    }


    fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<(f64, f64)>> {
        let (cx, cy) = self.get_center(node_idx)?; // Propagate error if get_center fails
        let (sx, sy) = self.get_size(node_idx)?;   // Propagate error if get_size fails
    
        Ok(vec![
            (cx - sx, cy - sy),
            (cx - sx, cy + sy),
            (cx + sx, cy - sy),
            (cx + sx, cy + sy),
        ])
    }

    fn find_nodes_in(&mut self, node_idx: usize) -> Vec<usize> {
        let mut results = Vec::new();
        self.collect_points(&mut results, node_idx);
        results
    }

    fn get_children_idxs(&self, index: usize) -> Vec<usize> {
        // self.nodes.get(index).map_or_else(Vec::new, |node| node.children.clone())
        self.nodes.get(index).map_or_else(Vec::new, |node| node.children.to_vec())
    }

    fn get_point_idxs(&self, node_idx: usize) -> Vec<usize> {
        self.nodes.get(node_idx)
            .and_then(|n| n.points.as_ref()) // Get points if node exists
            .map_or_else(Vec::new, |points| points.iter().map(|p| *p).collect())
    }



    fn query_polygon(&mut self, quadtree_points: Vec<(f64, f64)>, node_idx: usize, polygon_points: Option<Vec<(f64, f64)>>)  -> PyResult<HashSet<usize>> {
        // Simulating a function that returns a Result
        let mut results: HashSet<usize> = HashSet::new();

        let query_result: Result<(), Box<dyn Error>> = self._query_polygon(&quadtree_points, node_idx, polygon_points, &mut results);

        query_result.map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;

        Ok(results)
    }

}


impl QuadTree {

    const MAX: usize = 3;
    // const MAX: usize = 10;
    const MAX_DEPTH: i32 = 20;

    // // fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<(f64, f64)>> {
    // fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<(f64, f64)>> {
    //     let (cx, cy) = self.get_center(node_idx)?; // Propagate error if get_center fails
    //     let (sx, sy) = self.get_size(node_idx)?;   // Propagate error if get_size fails
        
    //     Ok(vec![
    //         (cx - sx, cy - sy),
    //         (cx - sx, cy + sy),
    //         (cx + sx, cy - sy),
    //         (cx + sx, cy + sy),
    //     ])
    // }

    // /// Get the center of a node
    // fn get_center(&self, index: usize) -> PyResult<(f64, f64)> {
    //     let nodes = &self.nodes;
    //     nodes.get(index).map(|n| n.center).ok_or_else(|| {
    //         pyo3::exceptions::PyIndexError::new_err("Invalid node index")
    //     })
    // }

    // fn find_nodes_in(&mut self, node_idx: usize) -> Vec<usize> {
    //     let mut results = Vec::new();
    //     self.collect_points(&mut results, node_idx);
    //     results
    // }

    // fn get_children_idxs(&self, index: usize) -> Vec<usize> {
    //     // self.nodes.get(index).map_or_else(Vec::new, |node| node.children.clone())
    //     self.nodes.get(index).map_or_else(Vec::new, |node| node.children.to_vec())
    // }

    // fn get_point_idxs(&self, node_idx: usize) -> Vec<usize> {
    //     self.nodes.get(node_idx)
    //         .and_then(|n| n.points.as_ref()) // Get points if node exists
    //         .map_or_else(Vec::new, |points| points.iter().map(|p| *p).collect())
    // }


    fn create_node(&mut self, center: (f64, f64), size: (f64, f64), depth: i32) -> usize {
        let mut nodes = &mut self.nodes;
        let index = nodes.len();
        nodes.push(QuadTreeNode {
            points: None,
            children: Vec::new(),
            center,
            size,
            depth,
        });
        index
    }

    fn get_depth(&self, index: usize) -> i32 {
        let nodes = &self.nodes;
        nodes.get(index).map(|n| n.depth).expect("Index exists in QuadTree arena")
    }

    fn get_points_length(&self, index: usize) -> usize{
        let nodes = &self.nodes;
        if let Some(n) = nodes.get(index) {
            let point_count = n.points.as_ref().map_or(0, |v| v.len());
            point_count
        } else {
            panic!("Index exists in QuadTree arena");
        }
    }

    fn get_size(&self, index: usize) -> PyResult<(f64, f64)> {
        let nodes = &self.nodes;
        nodes.get(index).map(|n| n.size).ok_or_else(|| {
            pyo3::exceptions::PyIndexError::new_err("Invalid node index")
        })
    }

    fn add_point_to_node(&mut self, index: usize, point_idx: usize) {
        if let Some(n) = self.nodes.get_mut(index) {
            // If the node already has points, check for duplicates
            if let Some(ref mut points) = n.points {
                if !points.iter().any(|pt| *pt == point_idx) {
                    points.push(point_idx);
                }
            } 
            // If there are no points yet, initialize the vector
            else {
                n.points = Some(vec![point_idx]);
            }
        }
    }
    
    fn insert(&mut self, pt_index: usize, node_idx: usize, pts_ref: &Vec<(f64, f64)>) {
        // Avoid allocating a new vector, check children directly
        if self.nodes[node_idx].children.is_empty() {
            // let node = QuadPoint::new(*item, pt_index);
            self.add_point_to_node(node_idx, pt_index);
    
            // Avoid multiple calls to `self.get_points_length(node_idx)`
            let points_len = self.get_points_length(node_idx);
            let depth = self.get_depth(node_idx);
    
            if points_len > Self::MAX && depth < Self::MAX_DEPTH {
                self.split(node_idx, pts_ref);
                // TODO: here, can remove the points attribute of the node with node_idx
                self.nodes[node_idx].points = None;
            }
        } else {
            self.insert_into_children(pt_index, node_idx, pts_ref);
        }
    }


    fn insert_into_children(&mut self, pt_index: usize, node_idx: usize, pts_ref: &Vec<(f64, f64)>) {
        // let (x, y) = *item;
        let (x,y) = pts_ref.get(pt_index).unwrap();
        let (cx, cy) = self.get_center(node_idx).unwrap();
        let child_idxs = self.get_children_idxs(node_idx);

        if *x <= cx {
            if *y <= cy {
                self.insert(pt_index, child_idxs[0], pts_ref);
            }
            if *y >= cy {
                self.insert(pt_index, child_idxs[1], pts_ref);
            }
        }
        if *x >= cx {
            if *y <= cy {
                self.insert(pt_index, child_idxs[2], pts_ref);
            }
            if *y >= cy {
                self.insert(pt_index, child_idxs[3], pts_ref);
            }
        }
    }

    fn add_child(&mut self, node_idx: usize, center: (f64, f64), size: (f64, f64), depth: i32) {
        let child_idx = self.create_node( center, size, depth);
        if let Some(n) = self.nodes.get_mut(node_idx) {
            n.children.push(child_idx);
        }
    }

    fn split(&mut self, node_idx: usize, pts_ref: &Vec<(f64, f64)>) {
        let (w, h) = self.get_size(node_idx).unwrap();
        let (x_center, y_center) = self.get_center(node_idx).unwrap();
        let node_depth = self.get_depth(node_idx);

        let (hx, hy) = (w * 0.5, h * 0.5);
    
        let new_centers = [
            (x_center - hx, y_center - hy),
            (x_center - hx, y_center + hy),
            (x_center + hx, y_center - hy),
            (x_center + hx, y_center + hy),
        ];
    
        // Add children
        for &center in &new_centers {
            self.add_child(node_idx, center, (hx, hy), node_depth + 1);
        }
    
        // Minimize locking scope
        let points = self.nodes.get_mut(node_idx).and_then(|n| n.points.take());
    
        // Process points outside the lock
        if let Some(points) = points {
            for node in points {
                self.insert_into_children(node, node_idx, pts_ref);
            }
        }
    }

    // fn collect_points(&mut self, results: &mut Vec<usize>, node_idx: usize) {
    //     let mut nodes = &mut self.nodes;

    //     if let Some(n) = nodes.get_mut(node_idx) {
    //         // NOTE: only push if point items aren't already in the node points
    //         if let Some(points) = &mut n.points {
    //             for point in points {
    //                 results.push(point.index);
    //             }
    //         }
    //     }
    //     let child_idxs = self.get_children_idxs(node_idx);
    //     for child_idx in child_idxs {
    //         self.collect_points(results, child_idx);
    //     }
    // }


    fn collect_points(&mut self, results: &mut Vec<usize>, node_idx: usize) {
        // Lock the nodes once and avoid locking multiple times
        let nodes = &self.nodes;
    
        // Start by collecting the points of the current node
        if let Some(n) = nodes.get(node_idx) {
            if let Some(points) = &n.points {
                results.extend(points.iter().map(|point| point)); // Use extend for more efficient pushing
            }
        }
    
        // Collect points from child nodes
        let mut stack = Vec::new(); // Use a stack to avoid recursion overhead
        stack.push(node_idx); // Start from the current node
    
        while let Some(current_node_idx) = stack.pop() {
            let child_idxs = self.get_children_idxs(current_node_idx);
            for child_idx in child_idxs {
                stack.push(child_idx); // Add children to stack for later processing
            }
    
            // Collect points of the child node
            if let Some(n) = nodes.get(current_node_idx) {
                if let Some(points) = &n.points {
                    results.extend(points.iter().map(|point| point)); // Efficiently extend the result
                }
            }
        }
    }

    fn get_node_items(&self, node_idx: usize) -> Vec<usize> {
        let nodes = &self.nodes;
        nodes.get(node_idx)
            .and_then(|n| n.points.as_ref()) // Get `points` only if node exists
            .map_or_else(Vec::new, |points| points.iter().map(|p| *p).collect())
    }


    // fn query_polygon(&mut self, quadtree_points: Vec<(f64, f64)>, node_idx: usize, polygon_points: Option<Vec<(f64, f64)>>) -> Result<HashSet<usize>, Box<dyn std::error::Error>>{
    //     let mut results: HashSet<usize> = HashSet::new();
    //     self._query_polygon(quadtree_points, node_idx, polygon_points, &mut results);
    //     Ok(results)
    // }

    fn _query_polygon(&mut self, quadtree_points: &Vec<(f64, f64)>, node_idx: usize, mut polygon_points: Option<Vec<(f64, f64)>>, results: &mut HashSet<usize>) -> Result<(), Box<dyn std::error::Error>>{
        if let Some(points) = polygon_points.as_mut() {
        // if !polygon_points.is_none() {
        //     let mut points = polygon_points.clone().unwrap();
            points.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
            // println!("HERE");
            // println!("{:?}", points);
            // println!{"{:?}", self.quadrant_rectangle_points(node_idx)?};
            if *points == self.quadrant_rectangle_points(node_idx)? {
                // println!("WERE EVER HERE IN SHORTCUT?");
                results.extend(self.find_nodes_in(node_idx));
                // println!("{:?}", results);
            }
            else {
                let children_idxs = self.get_children_idxs(node_idx);
                if children_idxs.len() > 0 {
                    let quadtree_center = self.get_center(node_idx)?;
                    let (left_polygon, right_polygon) = slice_in_two(polygon_points, quadtree_center.0, 0)?;
                    let (q1_polygon, q2_polygon) = slice_in_two(left_polygon, quadtree_center.1, 1)?;
                    let (q3_polygon, q4_polygon) = slice_in_two(right_polygon, quadtree_center.1, 1)?;
                    // println!("{:?}", results);
                    // println!("HERE");
                    // println!("{:?}", q1_polygon);
                    // println!{"{:?}", q2_polygon};
                    // println!("{:?}", q3_polygon);
                    // println!{"{:?}", q4_polygon};
                    self._query_polygon(quadtree_points, children_idxs[0], q1_polygon, results);
                    self._query_polygon(quadtree_points, children_idxs[1], q2_polygon, results);
                    self._query_polygon(quadtree_points, children_idxs[2], q3_polygon, results);
                    self._query_polygon(quadtree_points, children_idxs[3], q4_polygon, results);
                }
                // TODO: try optimisation: take bbox of polygon and quickly remove the results that are not in bbox already
                
                // println!("HERE");
                // println!("{:?}", self
                // .get_point_idxs(node_idx)
                // .into_iter()
                // .map(|node| quadtree_points[node]).collect::<Vec<_>>());
                // println!("{:?}", self.get_point_idxs(node_idx));
                // println!("{:?}", children_idxs.len());
                // println!{"{:?}", points};
                else {
                    // println!("HERE");
                    // println!("{:?}", self.get_point_idxs(node_idx));
                    // println!("{:?}", children_idxs.len());
                    // println!{"{:?}", points};
                    let filtered_nodes: Vec<usize> = self
                        .get_point_idxs(node_idx)
                        .into_iter()
                        .filter(|&node| is_contained_in(quadtree_points[node], &points))
                        .collect();
                    results.extend(filtered_nodes);
                }
            }
        }
        Ok(())
    }
    
}



#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadTree>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
}

fn is_contained_in(point: (f64, f64), polygon_points: &Vec<(f64, f64)>) -> bool {
    let (min_y_val, max_y_val) = _slice_2D_vertical_extents(&polygon_points, point.0);
    if min_y_val <= point.1 && point.1 <= max_y_val {
        return true
    }
    return false
}


fn _slice_2D_vertical_extents(polygon_points: &Vec<(f64, f64)>, val: f64) -> (f64, f64){
    let intersects = _find_intersects(&polygon_points, 0, val);
    // Take the min and max of the reduced intersects on the second axis
    let slice_axis_idx = 1;
    let (min_val, max_val) = intersects.into_iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY), // Start with extreme values
        |(min, max), (x, y)| {
            let value = if slice_axis_idx == 0 { x } else { y }; // Select the correct axis
            (min.min(value), max.max(value)) // Update min and max
        },
    );
    (min_val, max_val)
}


// RESTRICTED TO 2D POINTS FOR NOW
fn _find_intersects(polytope_points: &Vec<(f64, f64)>, slice_axis_idx: usize, value: f64) -> Vec<(f64, f64)>{
    let mut intersects: Vec<(f64, f64)> = vec![];
    let above_slice: Vec<(f64, f64)> = polytope_points
    .iter()
    .filter(|(x, y)| {
        let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
        value_to_compare >= value
    })
    .copied() // Convert `&(f64, f64)` to `(f64, f64)`
    .collect();

    let below_slice: Vec<(f64, f64)> = polytope_points
    .iter()
    .filter(|(x, y)| {
        let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
        value_to_compare <= value
    })
    .copied() // Convert `&(f64, f64)` to `(f64, f64)`
    .collect();


    for a in &above_slice {
        for b in &below_slice {
            // Edge is incident with the slice plane, store b in intersects
            if a.0 == b.0 && slice_axis_idx == 0 || a.1 == b.1 && slice_axis_idx == 1 {
                intersects.push(*b);
                continue;
            }
            let interp_coeff = (value - if slice_axis_idx == 0 { b.0 } else { b.1 }) 
                            / (if slice_axis_idx == 0 { a.0 - b.0 } else { a.1 - b.1 });

            let intersect = lerp(*a, *b, interp_coeff);
            // println!("HERE NOW LOOK");
            // println!("{:?}", intersect);
            // println!("{:?}", value);
            intersects.push(intersect);
        }
    }
    // println!("HERE");
    // println!("{:?}", polytope_points);
    // println!("{:?}", intersects);
    // println!{"{:?}", value};
    intersects
}


fn lerp(a: (f64, f64), b: (f64, f64), t: f64) -> (f64, f64) {
    (
        b.0 + t * (a.0 - b.0), // Linear interpolation for x
        b.1 + t * (a.1 - b.1), // Linear interpolation for y
    )
}

// def lerp(a, b, value):
//     intersect = [b + (a - b) * value for a, b in zip(a, b)]
//     return intersect


fn polygon_extents(polytope_points: &Vec<(f64, f64)>, slice_axis_idx: usize) -> (f64, f64){
    // let extents: (f64, f64) = 
    let (min_val, max_val) = polytope_points.into_iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY), // Start with extreme values
        |(min, max), &(x, y)| {
            let value = if slice_axis_idx == 0 { x } else { y }; // Select the correct axis
            (min.min(value), max.max(value)) // Update min and max
        },
    );
    (min_val, max_val)
}


fn slice_in_two(polytope_points: Option<Vec<(f64, f64)>>, value: f64, slice_axis_idx: usize)-> Result<(Option<Vec<(f64, f64)>>, Option<Vec<(f64, f64)>>), QhullError>{
    // println!("LOOK NOW");
    // println!("{:?}", value);
    if polytope_points.is_none() {
        return Ok((None, None))
    }
    else {
        // TODO: still to implement, placeholder
        let polytope_points_ref = polytope_points.as_ref().unwrap();
        let (x_lower, x_upper) = polygon_extents(polytope_points_ref, slice_axis_idx);
        let intersects = _find_intersects(polytope_points_ref, slice_axis_idx, value);

        if intersects.len() == 0 {
            if x_upper <= value {
                let left_polygon: Option<Vec<(f64, f64)>> = polytope_points;
                let right_polygon: Option<Vec<(f64, f64)>> = None;
                return Ok((left_polygon, right_polygon))
            }
            else if value < x_lower {
                let right_polygon: Option<Vec<(f64, f64)>> = polytope_points;
                let left_polygon: Option<Vec<(f64, f64)>> = None;
                return Ok((left_polygon, right_polygon))
            }
            else {
                // Will never be here
                return Ok((None, None))
            }
        }
        else {
            // let mut left_points: Vec<(f64, f64)> = polytope_points.clone().unwrap()
            //     .iter()
            //     .filter(|(x, y)| {
            //         let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
            //         value_to_compare <= value
            //     })
            //     .cloned() // Convert `&(f64, f64)` to `(f64, f64)`
            //     .collect();
            // let mut right_points: Vec<(f64, f64)> = polytope_points.clone().unwrap()
            //     .iter()
            //     .filter(|(x, y)| {
            //         let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
            //         value_to_compare >= value
            //     })
            //     .cloned() // Convert `&(f64, f64)` to `(f64, f64)`
            //     .collect();
            // left_points.extend(intersects.clone());
            // right_points.extend(intersects.clone());
            if let Some(polytope_points) = polytope_points.as_ref() {
                let left_points: Vec<(f64, f64)> = polytope_points
                    .iter()
                    .filter(|(x, y)| {
                        let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
                        value_to_compare <= value
                    })
                    .copied() // Avoids cloning, since (f64, f64) implements Copy
                    .collect();
            
                let right_points: Vec<(f64, f64)> = polytope_points
                    .iter()
                    .filter(|(x, y)| {
                        let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
                        value_to_compare >= value
                    })
                    .copied()
                    .collect();
            
                let mut left_points = left_points; // Rebind if mutation is necessary
                let mut right_points = right_points;
                
                left_points.extend(&intersects);  // Use reference to avoid cloning
                right_points.extend(&intersects);

                let left_polygon = find_qhull_points(left_points)?;
                let right_polygon = find_qhull_points(right_points)?;
                return Ok((left_polygon, right_polygon))
            }

            // let left_polygon = find_qhull_points(left_points)?;
            // let right_polygon = find_qhull_points(right_points)?;

            // return Ok((left_polygon, right_polygon))
            return Ok((None, None))
        }
    }
}


fn change_points_for_qhull(points: &Vec<(f64, f64)>) -> Vec<[f64; 2]> {
    // let converted: Vec<[f64; 2]> = points.clone()
    //     .into_iter()
    //     .map(|(x, y)| [x, y]) // Convert tuple into fixed-size array
    //     .collect();
    // converted
    points.into_iter().map(|&(x, y)| [x, y]).collect()
}


use std::fmt;

#[derive(Debug)]
enum QhullError {
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


fn find_qhull_points(points: Vec<(f64, f64)>) -> Result<Option<Vec<(f64, f64)>>, QhullError> {

    let converted = change_points_for_qhull(&points);
    let qh_result = Qh::builder()
    .compute(true)
    .build_from_iter(converted);

    // println!("NOW IN THE SLICING");
    // println!("{:?}", points);

    match qh_result {
        Ok(qh) => {
            let mut all_qhull_vertices: Vec<usize> = Vec::new();
            let mut all_qhull_vertices_: HashSet<usize> = HashSet::new();
            for simplex in qh.simplices() {
                let vertices = simplex
                    .vertices()
                    .unwrap()
                    .iter()
                    .map(|v| v.index(&qh).unwrap())
                    .collect::<Vec<_>>();
                
                for vertex in &vertices {
                    if all_qhull_vertices_.insert(*vertex) {
                        all_qhull_vertices.push(*vertex);
                    }
                }
            }

            let mut actual_qhull_points: Vec<(f64, f64)> = Vec::new();

            for idx in all_qhull_vertices {
                if let Some(point) = points.get(idx) {
                    actual_qhull_points.push(*point);
                }
            }

            // println!("{:?}", actual_qhull_points);
            Ok(Some(actual_qhull_points))
        }
        Err(e) => {
            let error_msg = e.to_string(); // Convert the error to a string

            if error_msg.contains("is flat") || error_msg.contains("less than"){
                Ok(None)
            } else {
                println!("QHull Error: {}", error_msg);
                return Err(QhullError::OtherError("QHull Error".to_string()));
            }
        }
    }
}

