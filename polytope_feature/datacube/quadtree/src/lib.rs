#![allow(dead_code)]

use std::collections::HashMap;
use std::convert::TryFrom;
use std::time::Instant;
use std::mem;
use pyo3::prelude::*;   // Do not use * for importing here
use pyo3::types::PyList;
use pyo3::exceptions::PyIndexError;
use pyo3::types::PyIterator;

use std::sync::{Arc, Mutex};


#[derive(Debug)]
#[derive(Clone)]
struct QuadPoint {
    item: (f64, f64),
    index: i64,
}


impl QuadPoint {
    fn new(item: (f64, f64), index: i64) -> Self {
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
    nodes: Arc<Mutex<Vec<QuadTreeNode>>>,
}

#[pymethods]
impl QuadTree {
    #[new]
    fn new() -> Self {
        QuadTree {
            nodes: Arc::new(Mutex::new(Vec::new())),
        }
    }

    fn create_node(&self, center: (f64, f64), size: (f64, f64), depth: i32) -> usize {
        let mut nodes = self.nodes.lock().unwrap();
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

    /// Get the center of a node
    fn get_center(&self, index: usize) -> PyResult<(f64, f64)> {
        let nodes = self.nodes.lock().unwrap();
        nodes.get(index).map(|n| n.center).ok_or_else(|| {
            pyo3::exceptions::PyIndexError::new_err("Invalid node index")
        })
    }

    fn get_size(&self, index: usize) -> PyResult<(f64, f64)> {
        let nodes = self.nodes.lock().unwrap();
        nodes.get(index).map(|n| n.size).ok_or_else(|| {
            pyo3::exceptions::PyIndexError::new_err("Invalid node index")
        })
    }


    fn build_point_tree(&mut self, points: Vec<(f64, f64)>){
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

}


impl QuadTree {
    
}



#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadTree>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
}












// fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
//     for (index, p) in points.iter().enumerate(){
//         self.insert(p, index.try_into().unwrap());
//     }
// }


// #[getter]
// fn children(&self, py: Python) -> Py<PyList> {
//     let py_list = PyList::empty(py);
//     for child in &self.children {
//         // py_list.append(child.clone()).unwrap();
//         // let py_child = PyCell::new(py, child.clone()).unwrap();
//         let py_child = unsafe {PyCell::new(py, child).unwrap().into();};
//         py_list.append(py_child).unwrap();
//     }
//     py_list.into()
// }


// #[getter]
// fn points(&self, py: Python) -> Py<PyList> {
//     let py_list = PyList::empty(py);
//     if let Some(ref pts) = self.points {
//         for point in pts {
//             // let py_point = PyCell::new(py, point.clone()).unwrap();
//             // py_list.append(py_point).unwrap();
//             py_list.append(point.index);
//         }
//     }
//     py_list.into()
// }

// fn find_nodes_in(&self) -> Vec<i64> {
//     let mut results = Vec::new();
//     self.collect_points(&mut results);
//     results
// }
// }

// impl QuadTreeNode {

// fn get_node_items(&self) -> Vec<&(f64, f64)> {
//     let mut node_items: Vec<&(f64, f64)> = vec![];
//     if let Some(points) = &self.points {
//         for point in points {
//             node_items.push(&point.item);
//         }
//     }
//     node_items
// }

// fn insert(&mut self, item: &(f64, f64), index: i64) {
//     if self.children.is_empty() {
//         let mut node = QuadPoint::new(*item, index);
//         let mut node_items: Vec<&(f64, f64)> = vec![];
//         if let Some(points) = self.points.as_mut() {
//             for point in &mut *points {
//                 node_items.push(&point.item);
//             }
//             if !node_items.contains(&item) {
//                 points.push(node);
//             }
//             if i32::try_from(points.len()).unwrap() > Self::MAX && self.depth < Self::MAX_DEPTH {
//                 self.split();
//             }
//         }
//     }
//     else {
//         self.insert_into_children(item, index);
//     }
// }

// fn insert_into_children(&mut self, item: &(f64, f64), index: i64) {
//     let (x, y) = *item;
//     let (cx, cy) = self.center;

//     if x <= cx {
//         if y <= cy {
//             self.children[0].insert(item, index);
//         }
//         if y >= cy {
//             self.children[1].insert(item, index);
//         }
//     }
//     if x >= cx {
//         if y <= cy {
//             self.children[2].insert(item, index);
//         }
//         if y >= cy {
//             self.children[3].insert(item, index);
//         }
//     }
// }

// fn split(&mut self) {

//     let (w, h) = self.size;
//     let hx: f64 = w/2.0;
//     let hy: f64 = h/2.0;
//     let (x_center, y_center) = self.center;
//     let new_centers: Vec<(f64, f64)> = vec![
//         (x_center - hx, y_center - hy),
//         (x_center - hx, y_center + hy),
//         (x_center + hx, y_center - hy),
//         (x_center + hx, y_center + hy),
//     ];

//     self.children = new_centers.into_iter().map(|(x, y)| QuadTreeNode::new(x, y, Some((hx, hy)), Some(self.depth + 1))).collect();

//     if let Some(points) = self.points.take() {
//         for node in points {
//             self.insert_into_children(&node.item, node.index);
//         }
//     }
// }


// /// **Recursive helper function (not exposed to Python)**
// fn collect_points(&self, results: &mut Vec<i64>) {
//     if let Some(points) = &self.points {
//         for point in points {
//             results.push(point.index); // Clone values instead of using references
//         }
//     }

//     for child in &self.children {
//         child.collect_points(results);
//     }
// }

