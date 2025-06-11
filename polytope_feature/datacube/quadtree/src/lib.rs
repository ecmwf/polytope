pub mod quadtree_mod;
pub mod slicing_tools;

use pyo3::prelude::*;

#[pymodule]
fn polytope_rs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<quadtree_mod::QuadTree>()?;
    m.add_class::<quadtree_mod::QuadTreeNode>()?;
    Ok(())
}