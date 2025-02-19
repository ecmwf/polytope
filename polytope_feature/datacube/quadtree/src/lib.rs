#![allow(dead_code)]

use pyo3::prelude::*;   // Do not use * for importing here

use std::sync::{Arc, Mutex};


#[derive(Debug)]
#[derive(Clone)]
struct QuadPoint {
    item: (f64, f64),
    index: usize,
}


impl QuadPoint {
    fn new(item: (f64, f64), index: usize) -> Self {
        Self {item, index}
    }
}

#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadTreeNode {
    points: Option<Vec<QuadPoint>>,
    children: Vec<usize>,

    #[pyo3(get, set)]
    center: (f64, f64),
    size: (f64, f64),
    depth: i32,
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

    // fn create_node(&mut self, center: (f64, f64), size: (f64, f64), depth: i32) -> usize {
    //     let mut nodes = &mut self.nodes;
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

    /// Get the center of a node
    fn get_center(&self, index: usize) -> PyResult<(f64, f64)> {
        let nodes = &self.nodes;
        nodes.get(index).map(|n| n.center).ok_or_else(|| {
            pyo3::exceptions::PyIndexError::new_err("Invalid node index")
        })
    }

    // fn get_size(&self, index: usize) -> PyResult<(f64, f64)> {
    //     let nodes = &self.nodes;
    //     nodes.get(index).map(|n| n.size).ok_or_else(|| {
    //         pyo3::exceptions::PyIndexError::new_err("Invalid node index")
    //     })
    // }

    fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
        self.create_node((0.0,0.0), (180.0, 90.0), 0);
        // for (index, p) in points.iter().enumerate(){
        //     self.insert(p, index.try_into().unwrap(), 0);
        // }
        points.into_iter().enumerate().for_each(|(index, p)| {
            self.insert(&p, index, 0);
        });
    }

    fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<(f64, f64)>> {
        let (cx, cy) = self.get_center(node_idx)?; // Propagate error if get_center fails
        let (sx, sy) = self.get_size(node_idx)?;   // Propagate error if get_size fails
    
        Ok(vec![
            (cx + sx, cy + sy),
            (cx + sx, cy - sy),
            (cx - sx, cy + sy),
            (cx - sx, cy - sy),
        ])
    }

    fn find_nodes_in(&mut self, node_idx: usize) -> Vec<usize> {
        let mut results = Vec::new();
        self.collect_points(&mut results, node_idx);
        results
    }

    fn get_children_idxs(&self, index: usize) -> Vec<usize> {
        let nodes = &self.nodes; // Lock the mutex to access the nodes

        // Safely get the node at the given index and access its children
        let node_child_idxs = match nodes.get(index) {
            Some(node) => &node.children,
            None => return vec![], // If index is out of bounds, return an empty vector
        };

        node_child_idxs.to_vec()
    }


    fn get_point_idxs(&self, node_idx: usize) -> Vec<usize> {
        let nodes = &self.nodes;

        let mut point_indexes = vec![];

        if let Some(n) = nodes.get(node_idx) {
            // NOTE: only push if point items aren't already in the node points
            if let Some(points) = &n.points {
                for point in points {
                    point_indexes.push(point.index);
                }
            }
        }
        point_indexes
    }
    

}


impl QuadTree {

    const MAX: usize = 3;
    const MAX_DEPTH: i32 = 20;


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


    // fn add_point_to_node(&mut self, index: usize, point: QuadPoint, item: &(f64, f64)) {
    //     let mut nodes = &mut self.nodes;
    //     if let Some(n) = nodes.get_mut(index) {
    //         // NOTE: only push if point items aren't already in the node points
    //         if let Some(points) = &mut n.points {
    //             let mut node_items: Vec<&(f64, f64)> = vec![];
    //             for pt in &mut *points {
    //                 node_items.push(&pt.item);
    //             }
    //             if !node_items.contains(&item) {
    //                 points.push(point);
    //             }
    //         }
    //         else {
    //             n.points = Some(vec![point]);
    //         }
    //     }
    // }

    // fn insert(&mut self, item: &(f64, f64), pt_index: usize, node_idx: usize) {
    //     let node_children = self.get_children_idxs(node_idx);
    //     if node_children.len() == 0 {
    //         let node = QuadPoint::new(*item, pt_index);
    //         self.add_point_to_node(node_idx, node, item);
    //         if self.get_points_length(node_idx) > Self::MAX.try_into().unwrap() && self.get_depth(node_idx) < Self::MAX_DEPTH {
    //             self.split(node_idx);
    //         }
    //     }
    //     else {
    //         self.insert_into_children(item, pt_index, node_idx);
    //     }
    // }

    fn add_point_to_node(&mut self, index: usize, point: QuadPoint, item: &(f64, f64)) {
        if let Some(n) = self.nodes.get_mut(index) {
            // If the node already has points, check for duplicates
            if let Some(ref mut points) = n.points {
                if !points.iter().any(|pt| pt.item == *item) {
                    points.push(point);
                }
            } 
            // If there are no points yet, initialize the vector
            else {
                n.points = Some(vec![point]);
            }
        }
    }
    
    fn insert(&mut self, item: &(f64, f64), pt_index: usize, node_idx: usize) {
        // Avoid allocating a new vector, check children directly
        if self.nodes[node_idx].children.is_empty() {
            let node = QuadPoint::new(*item, pt_index);
            self.add_point_to_node(node_idx, node, item);
    
            // Avoid multiple calls to `self.get_points_length(node_idx)`
            let points_len = self.get_points_length(node_idx);
            let depth = self.get_depth(node_idx);
    
            if points_len > Self::MAX && depth < Self::MAX_DEPTH {
                self.split(node_idx);
            }
        } else {
            self.insert_into_children(item, pt_index, node_idx);
        }
    }
    



    fn insert_into_children(&mut self, item: &(f64, f64), pt_index: usize, node_idx: usize) {
        let (x, y) = *item;
        let (cx, cy) = self.get_center(node_idx).unwrap();
        let child_idxs = self.get_children_idxs(node_idx);

        if x <= cx {
            if y <= cy {
                self.insert(item, pt_index, child_idxs[0]);
            }
            if y >= cy {
                self.insert(item, pt_index, child_idxs[1]);
            }
        }
        if x >= cx {
            if y <= cy {
                self.insert(item, pt_index, child_idxs[2]);
            }
            if y >= cy {
                self.insert(item, pt_index, child_idxs[3]);
            }
        }
    }

    fn add_child(&mut self, node_idx: usize, center: (f64, f64), size: (f64, f64), depth: i32) {
        let child_idx = self.create_node( center, size, depth);
        if let Some(n) = self.nodes.get_mut(node_idx) {
            n.children.push(child_idx);
        }
    }


    // fn split(&mut self, node_idx: usize) {
    //     let (w, h) = self.get_size(node_idx).unwrap();
    //     let hx: f64 = w/2.0;
    //     let hy: f64 = h/2.0;
    //     let (x_center, y_center) = self.get_center(node_idx).unwrap();
    //     let node_depth = self.get_depth(node_idx);
    //     let new_centers: Vec<(f64, f64)> = vec![
    //         (x_center - hx, y_center - hy),
    //         (x_center - hx, y_center + hy),
    //         (x_center + hx, y_center - hy),
    //         (x_center + hx, y_center + hy),
    //     ];

    //     for center in new_centers {
    //         self.add_child(node_idx, center, (hx, hy), node_depth + 1);
    //     }

    //     // Lock nodes
    //     let mut nodes = &mut self.nodes;
            
    //     // Get the node reference
    //     let points = nodes.get_mut(node_idx).and_then(|n| n.points.take());
        
    //     // Drop the lock by ending the scope
    //     drop(nodes);
        
    //     // Now, safely mutate `self`
    //     if let Some(points) = points {
    //         for node in points.iter() {
    //             self.insert_into_children(&node.item, node.index, node_idx);
    //         }
    //     }
    // }

    fn split(&mut self, node_idx: usize) {
        // if let (Some((w, h)), Some((x_center, y_center)), Some(node_depth)) = (
        //     self.get_size(node_idx),
        //     self.get_center(node_idx),
        //     self.get_depth(node_idx),
        // ) {
        
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
                self.insert_into_children(&node.item, node.index, node_idx);
            }
        }
        // }
    }

    fn collect_points(&mut self, results: &mut Vec<usize>, node_idx: usize) {
        let mut nodes = &mut self.nodes;

        if let Some(n) = nodes.get_mut(node_idx) {
            // NOTE: only push if point items aren't already in the node points
            if let Some(points) = &mut n.points {
                for point in points {
                    results.push(point.index);
                }
            }
        }

        let child_idxs = self.get_children_idxs(node_idx);

        for child_idx in child_idxs {
            self.collect_points(results, child_idx);
        }
    }


    fn get_node_items(&self, node_idx: usize) -> Vec<(f64, f64)> {
        let mut node_items: Vec<(f64, f64)> = vec![];
        let nodes = &self.nodes;
        if let Some(n) = nodes.get(node_idx) {
            // NOTE: only push if point items aren't already in the node points
            if let Some(points) = &n.points {
                for point in points {
                    node_items.push(point.item);
                }
            }
        }
        node_items
    }
}



#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadTree>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
}


