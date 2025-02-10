#![allow(dead_code)]

use std::collections::HashMap;
use std::convert::TryFrom;
use std::time::Instant;
use std::mem;
use pyo3::prelude::*;


#[derive(Debug)]
#[derive(Clone)]
#[pyclass]
struct QuadTreeNode {
    points: Option<Vec<QuadPoint>>,
    children: Vec<QuadTreeNode>,
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

    // fn find_nodes_in<'a>(&'a self, results: &mut Option<Vec<&'a QuadPoint>>) {
    //     // Ensure results is initialized
    //     results.get_or_insert_with(Vec::new);
    
    //     // Recursively search in children
    //     for child in &self.children {
    //         child.find_nodes_in(results); // Pass mutable reference
    //     }
    
    //     // Add current node's points to results
    //     if let Some(vec) = results.as_mut() {
    //         if let Some(points) = &self.points {
    //             vec.extend(points.iter());
    //         }
    //     }
    // }

    fn find_nodes_in(&self) -> Vec<QuadPoint> {
        let mut results = Vec::new();
        self.collect_points(&mut results);
        results
    }
}

impl QuadTreeNode {
    // fn quadrant_rectangle_points(&self) -> Vec<(f64, f64)> {
    //     let (cx, cy) = self.center;
    //     let (sx, sy) = self.size;

    //     let mut rect_points: Vec<(f64, f64)> = Vec::new();

    //     rect_points.push((cx + sx, cy + sy));
    //     rect_points.push((cx + sx, cy - sy));
    //     rect_points.push((cx - sx, cy + sy));
    //     rect_points.push((cx - sx, cy - sy));

    //     rect_points
    // }

    // fn build_point_tree(&mut self, points: Vec<(f64, f64)>) {
    //     for (index, p) in points.iter().enumerate(){
    //         self.insert(p, index.try_into().unwrap());
    //     }
    // }

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
        // println!("HERE");
        if self.children.is_empty() {
            // println!("NOW");
            let mut node = QuadPoint::new(*item, index);
            // let node_items: Vec<&(f64, f64)> = self.get_node_items();
            let mut node_items: Vec<&(f64, f64)> = vec![];
            if let Some(points) = self.points.as_mut() {
                for point in &mut *points {
                    node_items.push(&point.item);
                }
            // }
            // if let Some(points) = self.points.as_mut() {
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

    // fn find_nodes_in<'a>(&'a self, results: &mut Option<Vec<&'a QuadPoint>>) {
    //     // Ensure results is initialized
    //     results.get_or_insert_with(Vec::new);
    
    //     // Recursively search in children
    //     for child in &self.children {
    //         child.find_nodes_in(results); // Pass mutable reference
    //     }
    
    //     // Add current node's points to results
    //     if let Some(vec) = results.as_mut() {
    //         if let Some(points) = &self.points {
    //             vec.extend(points.iter());
    //         }
    //     }
    // }

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

    // let point_cloud: Vec<(f64, f64)> = 
    // let n = 10000; // Number of points
    // let point_cloud: Vec<(f64, f64)> = (0..n)
    //     .map(|i| (i as f64 * 0.1, i as f64 * 0.2)) // Example function
    //     .collect();

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

