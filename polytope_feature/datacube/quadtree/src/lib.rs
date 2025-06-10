#![allow(dead_code)]

use pyo3::prelude::*;   // Do not use * for importing here

use std::collections::HashSet;
use std::error::Error;
use pyo3::exceptions::PyRuntimeError;

// TODO: look at rust built in arena

mod slicing_tools;

use slicing_tools::{is_contained_in, slice_in_two};

use std::cell::Cell;
use typed_arena::Arena;
use std::cell::RefCell;



// TODO: can we not replace this QuadPoint by just the index of the point in the list potentially?

#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadTreeNode<'a> {
    points: Option<Vec<usize>>,
    // children: Option<[&'static QuadTreeNode; 4]>,
    children: Option<[&'a RefCell<QuadTreeNode<'a>>; 4]>,
    #[pyo3(get, set)]
    center: (f64, f64),
    size: (f64, f64),
    depth: i32,
}

impl QuadTreeNode {
    fn new(center: (f64, f64), size: (f64, f64), depth:i32) -> Self {
        QuadTreeNode {
            points: None,
            children: None,
            center,
            size,
            depth
        }
    }
}

#[pyclass]
struct QuadTree {
    arena: Arena<QuadTreeNode>,
    root: Option<&'static QuadTreeNode>,
}

#[pymethods]
impl QuadTree {
    #[new]
    fn new() -> Self {
        QuadTree {
            arena: Arena::new(),
            root: None,
        }
    }

    fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
        let mut node = QuadTreeNode::new((0.0,0.0), (180.0, 90.0), 0);
        for (index, _p) in points.iter().enumerate() {
            self.insert(index, &mut node, &points);
        }

        let root = self.arena.alloc(node);
    }
}




// #[pymethods]
// impl QuadTree {


    // fn query_polygon(&mut self, quadtree_points: Vec<(f64, f64)>, node_idx: usize, mut polygon_points: Option<Vec<(f64, f64)>>)  -> PyResult<HashSet<usize>> {
    //     let mut results: HashSet<usize> = HashSet::new();

    //     let processed_quadtree_points = self.process_points(quadtree_points);

    //     let mut processed_polygon_points: Option<Vec<[f64; 2]>> = polygon_points
    //         .take()
    //         .map(|pts| pts.into_iter().map(|(x, y)| [x, y]).collect());

    //     let query_result: Result<(), Box<dyn Error>> = self._query_polygon(&processed_quadtree_points, node_idx, processed_polygon_points.as_mut(), &mut results);

    //     query_result.map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;

    //     Ok(results)
    // }

    // fn get_center(&self, index: usize) -> PyResult<(f64, f64)> {
    //     let nodes = &self.nodes;
    //     nodes.get(index).map(|n| n.center).ok_or_else(|| {
    //         pyo3::exceptions::PyIndexError::new_err("Invalid node index")
    //     })
    // }

    // fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<[f64; 2]>> {
    //     let (cx, cy) = self.get_center(node_idx)?;
    //     let (sx, sy) = self.get_size(node_idx)?; 
    
    //     Ok(vec![
    //         [cx - sx, cy - sy],
    //         [cx - sx, cy + sy],
    //         [cx + sx, cy - sy],
    //         [cx + sx, cy + sy],
    //     ])
    // }

    // fn find_nodes_in(&mut self, node_idx: usize) -> Vec<usize> {
    //     let mut results = Vec::new();
    //     self.collect_points(&mut results, node_idx);
    //     results
    // }

    // fn get_children_idxs(&self, index: usize) -> Vec<usize> {
    //     self.nodes.get(index).map_or_else(Vec::new, |node| node.children.to_vec())
    // }

    // fn get_point_idxs(&self, node_idx: usize) -> Vec<usize> {
    //     self.nodes.get(node_idx)
    //         .and_then(|n| n.points.as_ref()) // Get points if node exists
    //         .map_or_else(Vec::new, |points| points.iter().map(|p| *p).collect())
    // }

// }


impl QuadTree {

    const MAX: usize = 3;
    const MAX_DEPTH: i32 = 20;

    fn insert(&mut self, pt_index: usize, node: &mut QuadTreeNode, pts_ref: &Vec<(f64, f64)>) {
        if let Some(children) = node.children {
            if children.is_empty() {
                self.add_point_to_node(node, pt_index);
                let points_len = node.points.as_ref().map_or(0, |v| v.len());
                let depth = node.depth;
        
                if points_len > Self::MAX && depth < Self::MAX_DEPTH {
                    // self.split(node, pts_ref);
                    // TODO: here, can remove the points attribute of the node with node_idx
                    node.points = None;
                }
            } 
        }
        // else {
        //     self.insert_into_children(pt_index, node, pts_ref);
        // }
    }

    fn add_point_to_node(&mut self, n: &mut QuadTreeNode, point_idx: usize) {
        if let Some(ref mut points) = n.points {
            if !points.iter().any(|pt| *pt == point_idx) {
                points.push(point_idx);
            }
        } 
        else {
            n.points = Some(vec![point_idx]);
        }
    }

    fn insert_into_children(&mut self, pt_index: usize, node: &mut QuadTreeNode, pts_ref: &Vec<(f64, f64)>) {
        let (x,y) = pts_ref.get(pt_index).unwrap();
        let (cx, cy) = node.center;
        // let children = node.children?;

        if let Some(mut children) = node.children {
            if *x <= cx {
                if *y <= cy {
                    self.insert(pt_index, children[0], pts_ref);
                }
                if *y >= cy {
                    self.insert(pt_index, children[1], pts_ref);
                }
            }
            if *x >= cx {
                if *y <= cy {
                    self.insert(pt_index, children[2], pts_ref);
                }
                if *y >= cy {
                    self.insert(pt_index, children[3], pts_ref);
                }
            }
        }
    }


    // fn process_points(&self, points: Vec<(f64, f64)>) -> Vec<[f64;2]> {
    //     points.into_iter().map(|(x, y)| [x,y]).collect()
    // }

    // fn create_node(&mut self, center: (f64, f64), size: (f64, f64), depth: i32) -> usize {
    //     let nodes = &mut self.nodes;
    //     let index = nodes.len();
    //     nodes.push(QuadTreeNode {
    //         points: None,
    //         children: Vec::new(),
    //         center,
    //         size,
    //         depth,
    //     });
    //     index
    // }

    // fn get_depth(&self, index: usize) -> i32 {
    //     let nodes = &self.nodes;
    //     nodes.get(index).map(|n| n.depth).expect("Index exists in QuadTree arena")
    // }

    // fn get_size(&self, index: usize) -> PyResult<(f64, f64)> {
    //     let nodes = &self.nodes;
    //     nodes.get(index).map(|n| n.size).ok_or_else(|| {
    //         pyo3::exceptions::PyIndexError::new_err("Invalid node index")
    //     })
    // }
    
    // fn insert(&mut self, pt_index: usize, node_idx: usize, pts_ref: &Vec<(f64, f64)>) {
    //     if self.nodes[node_idx].children.is_empty() {
    //         self.add_point_to_node(node_idx, pt_index);
    //         let points_len = self.get_points_length(node_idx);
    //         let depth = self.get_depth(node_idx);
    
    //         if points_len > Self::MAX && depth < Self::MAX_DEPTH {
    //             self.split(node_idx, pts_ref);
    //             // TODO: here, can remove the points attribute of the node with node_idx
    //             self.nodes[node_idx].points = None;
    //         }
    //     } else {
    //         self.insert_into_children(pt_index, node_idx, pts_ref);
    //     }
    // }


    // fn insert_into_children(&mut self, pt_index: usize, node_idx: usize, pts_ref: &Vec<(f64, f64)>) {
    //     let (x,y) = pts_ref.get(pt_index).unwrap();
    //     let (cx, cy) = self.get_center(node_idx).unwrap();
    //     let child_idxs = self.get_children_idxs(node_idx);

    //     if *x <= cx {
    //         if *y <= cy {
    //             self.insert(pt_index, child_idxs[0], pts_ref);
    //         }
    //         if *y >= cy {
    //             self.insert(pt_index, child_idxs[1], pts_ref);
    //         }
    //     }
    //     if *x >= cx {
    //         if *y <= cy {
    //             self.insert(pt_index, child_idxs[2], pts_ref);
    //         }
    //         if *y >= cy {
    //             self.insert(pt_index, child_idxs[3], pts_ref);
    //         }
    //     }
    // }

    // fn add_child(&mut self, node_idx: usize, center: (f64, f64), size: (f64, f64), depth: i32) {
    //     let child_idx = self.create_node( center, size, depth);
    //     if let Some(n) = self.nodes.get_mut(node_idx) {
    //         n.children.push(child_idx);
    //     }
    // }

    // fn split(&mut self, node_idx: usize, pts_ref: &Vec<(f64, f64)>) {
    //     let (w, h) = self.get_size(node_idx).unwrap();
    //     let (x_center, y_center) = self.get_center(node_idx).unwrap();
    //     let node_depth = self.get_depth(node_idx);

    //     let (hx, hy) = (w * 0.5, h * 0.5);
    
    //     let new_centers = [
    //         (x_center - hx, y_center - hy),
    //         (x_center - hx, y_center + hy),
    //         (x_center + hx, y_center - hy),
    //         (x_center + hx, y_center + hy),
    //     ];
    
    //     // Add children
    //     for &center in &new_centers {
    //         self.add_child(node_idx, center, (hx, hy), node_depth + 1);
    //     }
    
    //     // Minimize locking scope
    //     let points = self.nodes.get_mut(node_idx).and_then(|n| n.points.take());
    
    //     // Process points outside the lock
    //     if let Some(points) = points {
    //         for node in points {
    //             self.insert_into_children(node, node_idx, pts_ref);
    //         }
    //     }
    // }


    // fn collect_points(&mut self, results: &mut Vec<usize>, node_idx: usize) {
    //     let nodes = &self.nodes;
    
    //     if let Some(n) = nodes.get(node_idx) {
    //         if let Some(points) = &n.points {
    //             results.extend(points.iter().map(|point| point));
    //         }
    //     }

    //     let mut stack = Vec::new();
    //     stack.push(node_idx);
    
    //     while let Some(current_node_idx) = stack.pop() {
    //         let child_idxs = self.get_children_idxs(current_node_idx);
    //         for child_idx in child_idxs {
    //             stack.push(child_idx); // Add children to stack for later processing
    //         }
    
    //         // Collect points of the child node
    //         if let Some(n) = nodes.get(current_node_idx) {
    //             if let Some(points) = &n.points {
    //                 results.extend(points.iter().map(|point| point)); // Efficiently extend the result
    //             }
    //         }
    //     }
    // }

    // fn get_node_items(&self, node_idx: usize) -> Vec<usize> {
    //     let nodes = &self.nodes;
    //     nodes.get(node_idx)
    //         .and_then(|n| n.points.as_ref()) // Get `points` only if node exists
    //         .map_or_else(Vec::new, |points| points.iter().map(|p| *p).collect())
    // }

    // fn _query_polygon(
    //     &mut self,
    //     quadtree_points: &Vec<[f64; 2]>,
    //     node_idx: usize,
    //     polygon_points: Option<&mut Vec<[f64; 2]>>,
    //     results: &mut HashSet<usize>,
    // ) -> Result<(), Box<dyn std::error::Error>> {
    //     if let Some(points) = polygon_points {
    //         // Sort points based on the first coordinate
    //         points.sort_unstable_by(|a, b| a[0].partial_cmp(&b[0]).unwrap());
    
    //         if *points == self.quadrant_rectangle_points(node_idx)? {
    //             results.extend(self.find_nodes_in(node_idx));
    //         } else {
    //             let children_idxs = self.get_children_idxs(node_idx);
    //             if !children_idxs.is_empty() {
    //                 let quadtree_center = self.get_center(node_idx)?;
    
    //                 let (left_polygon, right_polygon) = slice_in_two(Some(points), quadtree_center.0, 0)?;
    //                 let (q1_polygon, q2_polygon) = slice_in_two(left_polygon.as_ref(), quadtree_center.1, 1)?;
    //                 let (q3_polygon, q4_polygon) = slice_in_two(right_polygon.as_ref(), quadtree_center.1, 1)?;
    
    //                 if let Some(mut poly) = q1_polygon {
    //                     self._query_polygon(quadtree_points, children_idxs[0], Some(poly.as_mut()), results)?;
    //                 }
    //                 if let Some(mut poly) = q2_polygon {
    //                     self._query_polygon(quadtree_points, children_idxs[1], Some(poly.as_mut()), results)?;
    //                 }
    //                 if let Some(mut poly) = q3_polygon {
    //                     self._query_polygon(quadtree_points, children_idxs[2], Some(poly.as_mut()), results)?;
    //                 }
    //                 if let Some(mut poly) = q4_polygon {
    //                     self._query_polygon(quadtree_points, children_idxs[3], Some(poly.as_mut()), results)?;
    //                 }
    //             } else {
    //                 let filtered_nodes: Vec<usize> = self
    //                     .get_point_idxs(node_idx)
    //                     .into_iter()
    //                     .filter(|&node| is_contained_in(quadtree_points[node], &points))
    //                     .collect();
    //                 results.extend(filtered_nodes);
    //             }
    //         }
    //     }
    //     Ok(())
    // }
}



#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadTree>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
}

