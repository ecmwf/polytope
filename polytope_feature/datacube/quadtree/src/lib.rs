#![allow(dead_code)]

use std::collections::HashMap;
use std::convert::TryFrom;
use std::time::Instant;
use std::mem;
use pyo3::prelude::*;   // Do not use * for importing here
use pyo3::types::PyList;
use pyo3::exceptions::PyIndexError;
use pyo3::types::PyIterator;



#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadTreeNode {
    points: Option<Vec<QuadPoint>>,
    children: Vec<QuadTreeNode>,

    #[pyo3(get, set)]
    center: (f64, f64),
    size: (f64, f64),
    depth: i32,
}

#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadPoint {
    #[pyo3(get, set)]
    item: (f64, f64),
    #[pyo3(get, set)]
    index: i64,
}


#[pymethods]
impl QuadPoint {
    #[new]
    fn new(item: (f64, f64), index: i64) -> Self {
        Self {item, index}
    }
}


#[pymethods]
impl QuadTreeNode {

    const MAX: i32 = 3;
    const MAX_DEPTH: i32 = 20;

    #[new]
    fn new(x: f64, y: f64, size: Option<(f64, f64)>, depth: Option<i32>) -> Self {
        Self {
            points: Some(Vec::new()),
            children: Vec::new(),
            center: (x,y),
            size: size.unwrap_or((180.0, 90.0)),
            depth: depth.unwrap_or(0),
        }
    }

    fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
        for (index, p) in points.iter().enumerate(){
            self.insert(p, index.try_into().unwrap());
        }
    }

    fn quadrant_rectangle_points(&self) -> Vec<(f64, f64)> {
        let (cx, cy) = self.center;
        let (sx, sy) = self.size;

        let mut rect_points: Vec<(f64, f64)> = Vec::new();

        rect_points.push((cx + sx, cy + sy));
        rect_points.push((cx + sx, cy - sy));
        rect_points.push((cx - sx, cy + sy));
        rect_points.push((cx - sx, cy - sy));

        rect_points
    }

    /// Return the length of the vector
    fn __len__(&self) -> usize {
        self.children.len()
    }

    #[getter]
    fn points(&self, py: Python) -> Py<PyList> {
        let py_list = PyList::empty(py);
        if let Some(ref pts) = self.points {
            for point in pts {
                let py_point = PyCell::new(py, point.clone()).unwrap();
                py_list.append(py_point).unwrap();
            }
        }
        py_list.into()
    }

    fn find_nodes_in(&self) -> Vec<QuadPoint> {
        let mut results = Vec::new();
        self.collect_points(&mut results);
        results
    }
}

impl QuadTreeNode {

    fn get_node_items(&self) -> Vec<&(f64, f64)> {
        let mut node_items: Vec<&(f64, f64)> = vec![];
        if let Some(points) = &self.points {
            for point in points {
                node_items.push(&point.item);
            }
        }
        node_items
    }

    fn insert(&mut self, item: &(f64, f64), index: i64) {
        if self.children.is_empty() {
            let mut node = QuadPoint::new(*item, index);
            let mut node_items: Vec<&(f64, f64)> = vec![];
            if let Some(points) = self.points.as_mut() {
                for point in &mut *points {
                    node_items.push(&point.item);
                }
                if !node_items.contains(&item) {
                    points.push(node);
                }
                if i32::try_from(points.len()).unwrap() > Self::MAX && self.depth < Self::MAX_DEPTH {
                    self.split();
                }
            }
        }
        else {
            self.insert_into_children(item, index);
        }
    }

    fn insert_into_children(&mut self, item: &(f64, f64), index: i64) {
        let (x, y) = *item;
        let (cx, cy) = self.center;

        if x <= cx {
            if y <= cy {
                self.children[0].insert(item, index);
            }
            if y >= cy {
                self.children[1].insert(item, index);
            }
        }
        if x >= cx {
            if y <= cy {
                self.children[2].insert(item, index);
            }
            if y >= cy {
                self.children[3].insert(item, index);
            }
        }
    }

    fn split(&mut self) {

        let (w, h) = self.size;
        let hx: f64 = w/2.0;
        let hy: f64 = h/2.0;
        let (x_center, y_center) = self.center;
        let new_centers: Vec<(f64, f64)> = vec![
            (x_center - hx, y_center - hy),
            (x_center - hx, y_center + hy),
            (x_center + hx, y_center - hy),
            (x_center + hx, y_center + hy),
        ];

        self.children = new_centers.into_iter().map(|(x, y)| QuadTreeNode::new(x, y, Some((hx, hy)), Some(self.depth + 1))).collect();

        if let Some(points) = self.points.take() {
            for node in points {
                self.insert_into_children(&node.item, node.index);
            }
        }
    }


    /// **Recursive helper function (not exposed to Python)**
    fn collect_points(&self, results: &mut Vec<QuadPoint>) {
        if let Some(points) = &self.points {
            for point in points {
                results.push(point.clone()); // Clone values instead of using references
            }
        }
    
        for child in &self.children {
            child.collect_points(results);
        }
    }

    fn heap_size(&self) -> usize {
        let mut total_size = 0;

        // Count memory used by `points` vector
        if let Some(points) = &self.points {
            total_size += mem::size_of_val(points) + (points.len() * mem::size_of::<QuadPoint>());
        }

        // Count memory used by `children` vector
        total_size += mem::size_of_val(&self.children) + (self.children.len() * mem::size_of::<QuadTreeNode>());

        // Recursively add children's heap size
        for child in &self.children {
            total_size += child.heap_size();
        }

        total_size
    }

}

#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadPoint>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
}


fn main() {
    let mut quadtree: QuadTreeNode = QuadTreeNode::new(0.0, 0.0, Some((180.0, 90.0)), Some(0));
    println!("{:?}", quadtree.quadrant_rectangle_points());
    quadtree.insert(&(50.0, 50.0), 0);
    if let Some(ref points) = quadtree.points {
        println!("{}", points.len());
        println!("{:?}", points[0].item);
    }

    let dx = 0.1;
    let dy= 0.25;

    let mut grid = Vec::new();
    
    let mut x = -180.0;
    while x <= 180.0 {
        let mut y = -90.0;
        while y <= 90.0 {
            grid.push((x, y));
            y += dy;
        }
        x += dx;
    }

    println!("{}", grid.len());
    let start = Instant::now();
    quadtree.build_point_tree(grid);
    let duration = start.elapsed();
    // println!("{:?}", quadtree);
    println!("Time taken: {:?}", duration);
    println!("Memory of the tree: {:?}", quadtree.heap_size() + mem::size_of_val(&quadtree));
}



// NOTE: everything/ every method that has to do with Polytope objects can be implemented in Python 
// as a standalone method which takes in the Python objects and the QuadPoint or QuadTreeNode

