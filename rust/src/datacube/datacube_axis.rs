use std::any::Any;

pub trait DatacubeAxis: std::fmt::Debug  {
    fn parse(&self, value: &dyn Any) -> Box<dyn Any>;
    fn to_float(&self, value: &dyn Any) -> Option<f64>;
    fn from_float(&self, value: f64) -> Box<dyn Any>;
    fn serialize(&self, value: &dyn Any) -> Box<dyn Any>;
}

#[derive(Debug)]
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


#[derive(Debug)]
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



// // Timestamp

// #[derive(Debug)]
// pub struct PandasTimestampDatacubeAxis {
//     pub name: String,
//     pub tol: f64,
//     pub can_round: bool,
//     pub range: (f64, f64),
//     pub type_: f64,
// }

// impl PandasTimestampDatacubeAxis {
//     pub fn new() -> Self {
//         Self {
//             name: "timestamp_axis".to_string(),
//             tol: 1e-12,
//             can_round: false,
//             range: (0., 1.), //TODO
//             type_: 0., // TODO
//         }
//     }
// }

// impl DatacubeAxis for PandasTimestampDatacubeAxis {
//     fn parse(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
//         // TODO
//         if let Some(v) = value.downcast_ref::<f64>() {
//             Box::new(*v)
//         } else {
//             Box::new("invalid")
//         }
//     }

//     fn to_float(&self, value: &dyn std::any::Any) -> Option<f64> {
//         // TODO
//         value.downcast_ref::<f64>().copied()
//     }

//     fn from_float(&self, value: f64) -> Box<dyn std::any::Any> {
//         // TODO
//         Box::new(value)
//     }

//     fn serialize(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
//         // TODO
//         if let Some(v) = value.downcast_ref::<f64>() {
//             Box::new(*v)
//         } else {
//             Box::new("invalid")
//         }
//     }
// }




// class PandasTimestampDatacubeAxis(DatacubeAxis):
//     def __init__(self):
//         self.name = None
//         self.tol = 1e-12
//         self.range = None
//         self.transformations = []
//         self.type = pd.Timestamp("2000-01-01T00:00:00")
//         self.can_round = False

//     def parse(self, value: Any) -> Any:
//         if isinstance(value, np.str_):
//             value = str(value)
//         return pd.Timestamp(value)

//     def to_float(self, value: pd.Timestamp):
//         if isinstance(value, np.datetime64):
//             return float((value - np.datetime64("1970-01-01T00:00:00")).astype("int"))
//         else:
//             return float(value.value / 10**9)

//     def from_float(self, value):
//         return pd.Timestamp(int(value), unit="s")

//     def serialize(self, value):
//         return str(value)

//     def offset(self, value):
//         return None


// class PandasTimedeltaDatacubeAxis(DatacubeAxis):
//     def __init__(self):
//         self.name = None
//         self.tol = 1e-12
//         self.range = None
//         self.transformations = []
//         self.type = np.timedelta64(0, "s")
//         self.can_round = False

//     def parse(self, value: Any) -> Any:
//         if isinstance(value, np.str_):
//             value = str(value)
//         return pd.Timedelta(value)

//     def to_float(self, value: pd.Timedelta):
//         if isinstance(value, np.timedelta64):
//             return value.astype("timedelta64[s]").astype(int)
//         else:
//             return float(value.value / 10**9)

//     def from_float(self, value):
//         return pd.Timedelta(int(value), unit="s")

//     def serialize(self, value):
//         return str(value)

//     def offset(self, value):
//         return None


// class UnsliceableDatacubeAxis(DatacubeAxis):
//     def __init__(self):
//         self.name = None
//         self.tol = float("NaN")
//         self.range = None
//         self.transformations = []
//         self.can_round = False

//     def parse(self, value: Any) -> Any:
//         return value

//     def to_float(self, value: pd.Timedelta):
//         raise TypeError("Tried to slice unsliceable axis")

//     def from_float(self, value):
//         raise TypeError("Tried to slice unsliceable axis")

//     def serialize(self, value):
//         raise TypeError("Tried to slice unsliceable axis")
