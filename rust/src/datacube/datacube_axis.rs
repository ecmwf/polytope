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



// Timestamp

use chrono::{DateTime, Utc, TimeZone};

#[derive(Debug)]
pub struct PandasTimestampDatacubeAxis {
    pub name: String,
    pub tol: f64,
    pub can_round: bool,
    pub range: (f64, f64),
    pub type_: DateTime<Utc>,
}

impl PandasTimestampDatacubeAxis {
    pub fn new() -> Self {
        Self {
            name: "timestamp_axis".to_string(),
            tol: 1e-12,
            can_round: false,
            range: (0., 1.),
            type_: Utc::now(),
        }
    }
}

impl DatacubeAxis for PandasTimestampDatacubeAxis {

    fn parse(&self, value: &dyn Any) -> Box<dyn Any> {
        if let Some(s) = value.downcast_ref::<&str>() {
            // Try parsing as RFC 3339 datetime
            match DateTime::parse_from_rfc3339(s) {
                Ok(dt) => Box::new(dt.with_timezone(&Utc)),
                Err(_) => Box::new("invalid datetime"),
            }
        } else if let Some(dt) = value.downcast_ref::<DateTime<Utc>>() {
            Box::new(*dt)
        } else {
            Box::new("invalid")
        }
    }

    fn to_float(&self, value: &dyn std::any::Any) -> Option<f64> {
        if let Some(dt) = value.downcast_ref::<DateTime<Utc>>() {
            Some(dt.timestamp() as f64)
        } else {
            None
    }
    }

    fn from_float(&self, value: f64) -> Box<dyn std::any::Any> {
        let s = value.trunc() as i64;
        let datetime: DateTime<Utc> = Utc.timestamp_opt(s, 0).unwrap();
        Box::new(datetime)
    }

    fn serialize(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {

        if let Some(dt) = value.downcast_ref::<DateTime<Utc>>() {
            Box::new(dt.to_rfc3339())
        } else {
            Box::new("invalid")
        }
    }
}




// class PandasTimestampDatacubeAxis(DatacubeAxis):

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
