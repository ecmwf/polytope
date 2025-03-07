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
    
}



#[pymodule]
fn quadtree(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<QuadTree>()?;
    m.add_class::<QuadTreeNode>()?;
    Ok(())
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
    .cloned() // Convert `&(f64, f64)` to `(f64, f64)`
    .collect();

    let below_slice: Vec<(f64, f64)> = polytope_points
    .iter()
    .filter(|(x, y)| {
        let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
        value_to_compare <= value
    })
    .cloned() // Convert `&(f64, f64)` to `(f64, f64)`
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
            intersects.push(intersect);
        }
    }
    intersects
}


fn lerp(a: (f64, f64), b: (f64, f64), t: f64) -> (f64, f64) {
    (
        a.0 + t * (b.0 - a.0), // Linear interpolation for x
        a.1 + t * (b.1 - a.1), // Linear interpolation for y
    )
}


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


fn slice_in_two(polytope_points: Option<Vec<(f64, f64)>>, value: f64, slice_axis_idx: usize)-> (Option<Vec<(f64, f64)>>, Option<Vec<(f64, f64)>>){
    if polytope_points.is_none() {
        return (None, None)
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
            }
            else if value < x_lower {
                let right_polygon: Option<Vec<(f64, f64)>> = polytope_points;
                let left_polygon: Option<Vec<(f64, f64)>> = None;
            }
        }
        else {
            let mut left_points: Vec<(f64, f64)> = polytope_points.clone().unwrap()
                .iter()
                .filter(|(x, y)| {
                    let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
                    value_to_compare <= value
                })
                .cloned() // Convert `&(f64, f64)` to `(f64, f64)`
                .collect();
            let mut right_points: Vec<(f64, f64)> = polytope_points.clone().unwrap()
                .iter()
                .filter(|(x, y)| {
                    let value_to_compare = if slice_axis_idx == 0 { *x } else { *y };
                    value_to_compare >= value
                })
                .cloned() // Convert `&(f64, f64)` to `(f64, f64)`
                .collect();
            left_points.extend(intersects.clone());
            right_points.extend(intersects.clone());
        }


        //         else:
        //             try:
        //                 hull = scipy.spatial.ConvexHull(left_points)
        //                 vertices = hull.vertices
        //             except scipy.spatial.qhull.QhullError as e:
        //                 if "less than" or "is flat" in str(e):
        //                     vertices = None

        //             if vertices is not None:
        //                 left_polygon = ConvexPolytope(polytope._axes, [left_points[i] for i in vertices])
        //             else:
        //                 left_polygon = None

        //             try:
        //                 hull = scipy.spatial.ConvexHull(right_points)
        //                 vertices = hull.vertices
        //             except scipy.spatial.qhull.QhullError as e:
        //                 if "less than" or "is flat" in str(e):
        //                     vertices = None

        //             if vertices is not None:
        //                 right_polygon = ConvexPolytope(polytope._axes, [right_points[i] for i in vertices])
        //             else:
        //                 right_polygon = None

        //         return (left_polygon, right_polygon)
        (None, None)
    }
}




// QHULL FUNCTIONS/TEST
fn try_qhull_functions(){
    let points: Vec<(f64, f64)> = vec![
        (0.0, 0.0),
        (1.0, 0.0),
        (0.5, 0.0),
        (0.0, 1.0),
    ];

    // Convert Vec<(f64, f64)> into Vec<[f64; 2]>
    let converted: Vec<[f64; 2]> = points.clone()
        .into_iter()
        .map(|(x, y)| [x, y]) // Convert tuple into fixed-size array
        .collect();
    
    // let qh_result = Qh::builder()
    // .compute(true)
    // .build_from_iter([
    //     // [0.25, 0.25],
    //     [0.0, 0.0],
    //     [1.0, 0.0],
    //     [0.5, 0.0],
    //     [0.0, 1.0],
    //     // [0.5, 0.5],
    //     // [3.0, 0.1]
    // ]);

    let qh_result = Qh::builder()
    .compute(true)
    .build_from_iter(converted);


    match qh_result {
        Ok(qh) => {
            println!("Convex hull computed successfully!");
            // let mut all_qhull_vertices: Vec<(f64, f64)> = Vec::new();
            // for simplex in qh.simplices() {
            //     let vertices = simplex
            //         .vertices().unwrap()
            //         .iter()
            //         .map(|v| v.index(&qh).unwrap())
            //         .collect::<Vec<_>>();
        
            //     // println!("{:?}", vertices);
        
            //     // let vertices = simplex
            //     //     .vertices();
            //     all_qhull_vertices.append(&mut vertices);
            //     println!("{:?}", vertices);
            // }
            
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
                    if all_qhull_vertices_.insert(*vertex) { // `insert()` returns false if already present
                        all_qhull_vertices.push(*vertex);
                    }
                }
                println!("{:?}", vertices);
            }
            println!("{:?}", all_qhull_vertices);

            let mut actual_qhull_points: Vec<(f64, f64)> = Vec::new();

            // TODO: push the points to a vector of the points
            for idx in all_qhull_vertices {
                // actual_qhull_points.push(points.get(idx))
                if let Some(point) = points.get(idx) {
                    actual_qhull_points.push(*point); // Dereference the reference to get the value
                }
            }

            println!("{:?}", actual_qhull_points);



            // let vertices = qh.vertices(); // Get convex hull vertices
            // let convex_hull_vertices: Vec<[f64; 2]> = vertices
            //     .iter()
            //     .map(|&i| points[i]) // Map indices to actual points
            //     .collect();
            // println!("Convex hull vertices: {:?}", convex_hull_vertices);
        }
        Err(e) => {
            let error_msg = e.to_string(); // Convert the error to a string

            if error_msg.contains("is flat") {
                println!("Had flat error message and handled it");
            } else {
                println!("Unhandled error: {}", error_msg);
            }
            // println!("Error computing convex hull: {}", e);

            // Handle the error, maybe return early or set a fallback value
        }
    }
}












// THIS SHOULD BE A QUADTREE METHOD
// def query_polygon(quadtree_points, quadtree: QuadTree, node_idx, polygon, results=None):
//     # intersect quad tree with a 2D polygon
//     if results is None:
//         results = set()

//     # intersect the children with the polygon
//     # TODO: here, we create None polygons... think about how to handle them
//     if polygon is None:
//         return results
//     else:
//         polygon_points = {tuple(point) for point in polygon.points}
//         # TODO: are these the right points which we are comparing, ie the points on the polygon
//         # and the points on the rectangle quadrant?
//         if sorted(list(polygon_points)) == quadtree.quadrant_rectangle_points(node_idx):
//             results.update(quadtree.find_nodes_in(node_idx))
//         else:
//             children_idxs = quadtree.get_children_idxs(node_idx)
//             if len(children_idxs) > 0:
//                 # first slice vertically
//                 quadtree_center = quadtree.get_center(node_idx)
//                 left_polygon, right_polygon = slice_in_two(polygon, quadtree_center[0], 0)

//                 # then slice horizontally
//                 # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

//                 q1_polygon, q2_polygon = slice_in_two(left_polygon, quadtree_center[1], 1)
//                 q3_polygon, q4_polygon = slice_in_two(right_polygon, quadtree_center[1], 1)

//                 # now query these 4 polygons further down the quadtree
//                 query_polygon(quadtree_points, quadtree, children_idxs[0], q1_polygon, results)
//                 query_polygon(quadtree_points, quadtree, children_idxs[1], q2_polygon, results)
//                 query_polygon(quadtree_points, quadtree, children_idxs[2], q3_polygon, results)
//                 query_polygon(quadtree_points, quadtree, children_idxs[3], q4_polygon, results)

//             # TODO: try optimisation: take bbox of polygon and quickly remove the results that are not in bbox already

//             results.update(
//                 node for node in quadtree.get_point_idxs(node_idx) if is_contained_in(quadtree_points[node], polygon)
//             )
//         return results
