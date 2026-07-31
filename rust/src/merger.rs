use pyo3::prelude::*;

#[pyclass]
#[derive(Clone)]
pub struct DatacubeAxisMerger {
    linkers: Vec<String>,
}

#[pymethods]
impl DatacubeAxisMerger {
    #[new]
    pub fn new(linkers: Vec<String>) -> Self {
        DatacubeAxisMerger { linkers }
    }

    fn __deepcopy__(&self, _memo: &PyAny) -> Self {
        self.clone()
    }

    /// Splits each merged value by linkers to recover first_val and second_val.
    /// Logic mirrors Python's unmerge:
    ///   first_val = merged_val[:first_idx]  (with "-" removed)
    ///   second_val = merged_val[first_idx + linker0_len : -linker1_len]  (with ":" removed)
    pub fn unmerge(&self, merged_vals: Vec<String>) -> (Vec<String>, Vec<String>) {
        let linker0 = &self.linkers[0];
        let linker1 = if self.linkers.len() > 1 { &self.linkers[1] } else { &self.linkers[0] };
        let first_linker_size = linker0.len();
        let second_linker_size = linker1.len();

        let mut first_values = Vec::with_capacity(merged_vals.len());
        let mut second_values = Vec::with_capacity(merged_vals.len());

        for merged_value in &merged_vals {
            let s = merged_value.as_str();
            let first_idx = match s.find(linker0.as_str()) {
                Some(idx) => idx,
                None => {
                    first_values.push(s.replace('-', ""));
                    second_values.push(String::new());
                    continue;
                }
            };

            let first_val = &s[..first_idx];
            let after_first_linker = first_idx + first_linker_size;
            let second_end = if s.len() > second_linker_size {
                s.len() - second_linker_size
            } else {
                s.len()
            };
            let second_val = if after_first_linker <= second_end {
                &s[after_first_linker..second_end]
            } else {
                ""
            };

            first_values.push(first_val.replace('-', ""));
            second_values.push(second_val.replace(':', ""));
        }

        (first_values, second_values)
    }
}
