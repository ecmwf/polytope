#![allow(dead_code)]

use pyo3::prelude::*;   // Do not use * for importing here

use std::sync::{Arc, Mutex};



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
            let points_size: usize = points.capacity() * size_of::<usize>();
            size += points_size;
        }
        // Dynamically allocated memory for children
        let children_size = self.children.capacity() * size_of::<usize>();
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
        let nodes_size: usize = self.nodes.capacity() * size_of::<QuadTreeNode>();
        size += nodes_size;
        // Sum sizes of each QuadTreeNode (including their allocated memory)
        for (i, node) in self.nodes.iter().enumerate() {
            let node_size = node.sizeof();
            size += node_size;
        }
        size
    }

    /// Get the center of a node
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

    // fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<Vec<(f64, f64)>> {
    fn quadrant_rectangle_points(&self, node_idx: usize) -> PyResult<[(f64, f64); 4]> {
        let (cx, cy) = self.get_center(node_idx)?; // Propagate error if get_center fails
        let (sx, sy) = self.get_size(node_idx)?;   // Propagate error if get_size fails
    
        Ok([
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
}


impl QuadTree {

    const MAX: usize = 3;
    // const MAX: usize = 10;
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
    
}



#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadTree>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
}


