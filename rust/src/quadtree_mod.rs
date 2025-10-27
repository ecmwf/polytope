#![allow(dead_code)]

use pyo3::prelude::*;   // Do not use * for importing here

use std::collections::HashSet;
use std::error::Error;
use pyo3::exceptions::PyRuntimeError;

// TODO: look at rust built in arena

use crate::slicing_tools::{is_contained_in, slice_in_two};
use crate::distance::{dist2, box_dist2};



#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
pub struct QuadTreeNode {
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
pub struct QuadTree {
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

    fn nearest_neighbor(&self, query: (f64, f64), quadtree_points: Vec<(f64, f64)>) -> Option<usize> {
        if self.nodes.is_empty() {
            return None;
        }
        let mut best_idx = None;
        let mut best_dist2 = f64::INFINITY;
        self.nn_search(0, query, &mut best_idx, &mut best_dist2, &quadtree_points);
        best_idx
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

    fn node_bbox_points(&self, node_idx: usize) -> PyResult<([f64; 2], [f64; 2])> {
        let (cx, cy) = self.get_center(node_idx)?;
        let (sx, sy) = self.get_size(node_idx)?;
        Ok((
            [cx - sx, cy - sy], // min corner
            [cx + sx, cy + sy], // max corner
        ))
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

    fn nn_search(
        &self,
        node_idx: usize,
        query: (f64, f64),
        best_idx: &mut Option<usize>,
        best_dist2: &mut f64,
        quadtree_points: &Vec<(f64, f64)>
    ) {
        let node = &self.nodes[node_idx];

        // if this node is farther than the current best, ignore
        if box_dist2(node.center, node.size, query) > *best_dist2 {
            return;
        }

        // compare distance of points inside leaf node
        if let Some(point_indices) = &node.points {
            for &pi in point_indices {
                let p = quadtree_points[pi];
                let d2 = dist2(p, query);
                if d2 < *best_dist2 {
                    *best_dist2 = d2;
                    *best_idx = Some(pi);
                }
            }
            return;
        }
        // else, recurse into children
        for &child_idx in &node.children {
            self.nn_search(child_idx, query, best_idx, best_dist2, &quadtree_points);
        }
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
        if self.nodes[node_idx].children.is_empty() {
            self.add_point_to_node(node_idx, pt_index);
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

    fn collect_points(&self, results: &mut Vec<usize>, node_idx: usize) {
        let mut stack = vec![node_idx];

        while let Some(current_node_idx) = stack.pop() {
            if let Some(node) = self.nodes.get(current_node_idx) {
                if let Some(points) = &node.points {
                    results.extend(points.iter()); // more concise and efficient
                }

                // Add children to the stack
                for &child_idx in self.get_children_idxs(current_node_idx).iter() {
                    stack.push(child_idx);
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
            points.sort_unstable_by(|a, b| a.partial_cmp(&b).unwrap());
            let mut quadrant_points = self.quadrant_rectangle_points(node_idx)?;
            if *points == quadrant_points {
                results.extend(self.find_nodes_in(node_idx));
            } else {
                let children_idxs = self.get_children_idxs(node_idx);
                if !children_idxs.is_empty() {
                    let quadtree_center = self.get_center(node_idx)?;

                    // TODO: optimisation: if polygon is entirely within one of the child quadrants, don't need to do slice_in_two really
    
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
