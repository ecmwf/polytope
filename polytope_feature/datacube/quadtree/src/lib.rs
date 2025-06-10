#![allow(dead_code)]

use pyo3::prelude::*;   // Do not use * for importing here

use qhull::Qh;
use std::collections::HashSet;
use std::error::Error;
use pyo3::exceptions::PyRuntimeError;
use qhull::*;

use std::cmp::Ordering::Equal;

// TODO: look at rust built in arena




// TODO: can we not replace this QuadPoint by just the index of the point in the list potentially?


#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadTreeNode {
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
        if let Some(points) = &self.points {
            let points_size: usize = points.len() * size_of::<usize>();
            size += points_size;
        }
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
        let mut size = size_of::<Self>();
        let nodes_size: usize = self.nodes.len() * size_of::<QuadTreeNode>();
        size += nodes_size;
        for (_i, node) in self.nodes.iter().enumerate() {
            let node_size = node.sizeof();
            size += node_size;
        }
        size
    }

    fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
        self.create_node((0.0,0.0), (180.0, 90.0), 0);
        points.iter().enumerate().for_each(|(index, _p)| {
            self.insert(index, 0, &points);
        });
    }


    fn query_polygon(&mut self, quadtree_points: Vec<(f64, f64)>, node_idx: usize, mut polygon_points: Option<Vec<(f64, f64)>>)  -> PyResult<HashSet<usize>> {
        let mut results: HashSet<usize> = HashSet::new();

        let processed_quadtree_points = self.process_points(quadtree_points);

        let mut processed_polygon_points: Option<Vec<[f64; 2]>> = polygon_points
            .take()
            .map(|pts| pts.into_iter().map(|(x, y)| [x, y]).collect());

        let query_result: Result<(), Box<dyn Error>> = self._query_polygon(&processed_quadtree_points, node_idx, processed_polygon_points.as_mut(), &mut results);

        query_result.map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;

        Ok(results)
    }

    fn get_center(&self, index: usize) -> PyResult<(f64, f64)> {
        let nodes = &self.nodes;
        nodes.get(index).map(|n| n.center).ok_or_else(|| {
            pyo3::exceptions::PyIndexError::new_err("Invalid node index")
        })
    }

    fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<[f64; 2]>> {
        let (cx, cy) = self.get_center(node_idx)?;
        let (sx, sy) = self.get_size(node_idx)?; 
    
        Ok(vec![
            [cx - sx, cy - sy],
            [cx - sx, cy + sy],
            [cx + sx, cy - sy],
            [cx + sx, cy + sy],
        ])
    }

    fn find_nodes_in(&mut self, node_idx: usize) -> Vec<usize> {
        let mut results = Vec::new();
        self.collect_points(&mut results, node_idx);
        results
    }

    fn get_children_idxs(&self, index: usize) -> Vec<usize> {
        self.nodes.get(index).map_or_else(Vec::new, |node| node.children.to_vec())
    }

    fn get_point_idxs(&self, node_idx: usize) -> Vec<usize> {
        self.nodes.get(node_idx)
            .and_then(|n| n.points.as_ref()) // Get points if node exists
            .map_or_else(Vec::new, |points| points.iter().map(|p| *p).collect())
    }

}


impl QuadTree {

    const MAX: usize = 3;
    const MAX_DEPTH: i32 = 20;

    fn process_points(&self, points: Vec<(f64, f64)>) -> Vec<[f64;2]> {
        points.into_iter().map(|(x, y)| [x,y]).collect()
    }

    fn convert_polygon(&self, points: Option<Vec<(f64, f64)>>) -> Option<Vec<[f64; 2]>> {
        points.map(|pts| pts.into_iter().map(|(x, y)| [x, y]).collect())
    }

    fn create_node(&mut self, center: (f64, f64), size: (f64, f64), depth: i32) -> usize {
        let nodes = &mut self.nodes;
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

    fn _query_polygon(
        &mut self,
        quadtree_points: &Vec<[f64; 2]>,
        node_idx: usize,
        polygon_points: Option<&mut Vec<[f64; 2]>>,
        results: &mut HashSet<usize>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        if let Some(points) = polygon_points {
            // Sort points based on the first coordinate
            points.sort_unstable_by(|a, b| a[0].partial_cmp(&b[0]).unwrap());
    
            if *points == self.quadrant_rectangle_points(node_idx)? {
                results.extend(self.find_nodes_in(node_idx));
            } else {
                let children_idxs = self.get_children_idxs(node_idx);
                if !children_idxs.is_empty() {
                    let quadtree_center = self.get_center(node_idx)?;
    
                    let (left_polygon, right_polygon) = slice_in_two(Some(points), quadtree_center.0, 0)?;
                    let (q1_polygon, q2_polygon) = slice_in_two(left_polygon.as_ref(), quadtree_center.1, 1)?;
                    let (q3_polygon, q4_polygon) = slice_in_two(right_polygon.as_ref(), quadtree_center.1, 1)?;
    
                    if let Some(mut poly) = q1_polygon {
                        self._query_polygon(quadtree_points, children_idxs[0], Some(poly.as_mut()), results)?;
                    }
                    if let Some(mut poly) = q2_polygon {
                        self._query_polygon(quadtree_points, children_idxs[1], Some(poly.as_mut()), results)?;
                    }
                    if let Some(mut poly) = q3_polygon {
                        self._query_polygon(quadtree_points, children_idxs[2], Some(poly.as_mut()), results)?;
                    }
                    if let Some(mut poly) = q4_polygon {
                        self._query_polygon(quadtree_points, children_idxs[3], Some(poly.as_mut()), results)?;
                    }
                } else {
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

fn is_contained_in(point: [f64; 2], polygon_points: &Vec<[f64; 2]>) -> bool {
    let (min_y_val, max_y_val) = _slice_2D_vertical_extents(&polygon_points, point[0]);
    point[1] >= min_y_val && point[1] <= max_y_val
}

fn _slice_2D_vertical_extents(polygon_points: &Vec<[f64; 2]>, val: f64) -> (f64, f64) {
    // Get the intersection points with the vertical slice at `val`
    let intersects = _find_intersects(polygon_points, 0, val);
    
    // Calculate the vertical extents (min and max Y-values) from the intersection points
    intersects.into_iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY),
        |(min, max), intersect| {
            let y = intersect[1];
            (min.min(y), max.max(y))
        },
    )
}

// RESTRICTED TO 2D POINTS FOR NOW
fn _find_intersects(polytope_points: &Vec<[f64; 2]>, slice_axis_idx: usize, value: f64) -> Vec<[f64; 2]>{
    let mut intersects: Vec<[f64; 2]> = vec![];
    let above_slice: Vec<[f64; 2]> = polytope_points
    .iter()
    .filter(|&point| {
        let value_to_compare = if slice_axis_idx == 0 { point[0] } else { point[1] };
        value_to_compare >= value
    })
    .copied() // Convert `&(f64, f64)` to `(f64, f64)`
    .collect();

    let below_slice: Vec<[f64; 2]> = polytope_points
    .iter()
    .filter(|&point| {
        let value_to_compare = if slice_axis_idx == 0 { point[0] } else { point[1] };
        value_to_compare <= value
    })
    .copied() // Convert `&(f64, f64)` to `(f64, f64)`
    .collect();


    for a in &above_slice {
        for b in &below_slice {
            // Edge is incident with the slice plane, store b in intersects
            if a[0] == b[0] && slice_axis_idx == 0 || a[1] == b[1] && slice_axis_idx == 1 {
                intersects.push(*b);
                continue;
            }
            let interp_coeff = (value - if slice_axis_idx == 0 { b[0] } else { b[1] }) 
                            / (if slice_axis_idx == 0 { a[0] - b[0] } else { a[1] - b[1] });

            let intersect = lerp(*a, *b, interp_coeff);
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

fn slice_in_two(
    polytope_points: Option<&Vec<[f64; 2]>>,
    value: f64,
    slice_axis_idx: usize,
) -> Result<(Option<Vec<[f64; 2]>>, Option<Vec<[f64; 2]>>), QhullError> {
    // Directly return if no points exist
    if let Some(polytope_points) = polytope_points {
        // Calculate the extents and intersections once
        let (x_lower, x_upper) = polygon_extents(&polytope_points, slice_axis_idx);
        let intersects: Vec<[f64; 2]> = _find_intersects(&polytope_points, slice_axis_idx, value);

        // If no intersections, directly handle the boundary cases
        if intersects.is_empty() {
            return Ok(if x_upper <= value {
                (Some(polytope_points.clone()), None)
            } else if value < x_lower {
                (None, Some(polytope_points.clone()))
            } else {
                (None, None) // Should never happen
            });
        }

        // Instead of partitioning into two vectors, we manually filter and extend
        let mut left_points: Vec<[f64; 2]> = Vec::with_capacity(polytope_points.len());
        let mut right_points: Vec<[f64; 2]> = Vec::with_capacity(polytope_points.len());

        for &point in polytope_points {
            let value_to_compare = point[slice_axis_idx];
            if value_to_compare <= value {
                left_points.push(point);
            } else {
                right_points.push(point);
            }
        }

        // Extend both left and right with intersection points
        left_points.extend(intersects.iter().cloned());
        right_points.extend(intersects.iter().cloned());

        // Convert the points into polygons using find_qhull_points
        let left_polygon = find_qhull_points3(&left_points)?;
        let right_polygon = find_qhull_points3(&right_points)?;

        return Ok((left_polygon, right_polygon));
    }
    // Return None for both left and right if no polytope_points provided
    Ok((None, None))
}


fn change_points_for_qhull(points: &[(f64, f64)]) -> Vec<[f64; 2]> {
    let mut result = Vec::with_capacity(points.len()); // Preallocate
    for &(x, y) in points {
        result.push([x, y]);
    }
    result
}


use geo::{LineString, Polygon, point, ConvexHull, CoordsIter};

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
