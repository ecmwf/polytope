use std::any::Any;

pub trait DatacubeAxis {
    fn parse(&self, value: &dyn Any) -> Box<dyn Any>;
    fn to_float(&self, value: &dyn Any) -> Option<f64>;
    fn from_float(&self, value: f64) -> Box<dyn Any>;
    fn serialize(&self, value: &dyn Any) -> Box<dyn Any>;
}


pub struct IntDatacubeAxis {
    pub name: String,
    pub tol: f64,
    pub can_round: bool,
    pub range: (i32, i32),
    pub type_: i32,
}

impl IntDatacubeAxis {
    pub fn new() -> Self {
        Self {
            name: "int_axis".to_string(),
            tol: 1e-12,
            can_round: true,
            range: (0, 1),
            type_: 0,
        }
    }
}

impl DatacubeAxis for IntDatacubeAxis {
    fn parse(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        if let Some(v) = value.downcast_ref::<f64>() {
            Box::new(*v)
        } else {
            Box::new("invalid")
        }
    }

    fn to_float(&self, value: &dyn std::any::Any) -> Option<f64> {
        value.downcast_ref::<f64>().copied()
    }

    fn from_float(&self, value: f64) -> Box<dyn std::any::Any> {
        Box::new(value)
    }

    fn serialize(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        if let Some(v) = value.downcast_ref::<i32>() {
            Box::new(*v)
        } else {
            Box::new("invalid")
        }
    }
}



pub struct FloatDatacubeAxis {
    pub name: String,
    pub tol: f64,
    pub can_round: bool,
    pub range: (f64, f64),
    pub type_: f64,
}

impl FloatDatacubeAxis {
    pub fn new() -> Self {
        Self {
            name: "float_axis".to_string(),
            tol: 1e-12,
            can_round: true,
            range: (0., 1.),
            type_: 0.,
        }
    }
}

impl DatacubeAxis for FloatDatacubeAxis {
    fn parse(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        if let Some(v) = value.downcast_ref::<f64>() {
            Box::new(*v)
        } else {
            Box::new("invalid")
        }
    }

    fn to_float(&self, value: &dyn std::any::Any) -> Option<f64> {
        value.downcast_ref::<f64>().copied()
    }

    fn from_float(&self, value: f64) -> Box<dyn std::any::Any> {
        Box::new(value)
    }

    fn serialize(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        if let Some(v) = value.downcast_ref::<f64>() {
            Box::new(*v)
        } else {
            Box::new("invalid")
        }
    }
}