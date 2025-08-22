use std::any::Any;

pub trait DatacubeAxis: std::fmt::Debug  {
    fn parse(&self, value: &dyn Any) -> Box<dyn Any>;
    fn to_float(&self, value: &dyn Any) -> Option<f64>;
    fn from_float(&self, value: f64) -> Box<dyn Any>;
    fn serialize(&self, value: &dyn Any) -> Box<dyn Any>;
    fn offset(&self, value: &dyn Any) -> Option<Box<dyn Any>> {
        Some(Box::new(0))
    }
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

    fn offset(&self, value: &dyn Any) -> Option<Box<dyn Any>>{
        None
    }
}

// Timedelta

use chrono::{Duration};

#[derive(Debug)]
pub struct PandasTimedeltaDatacubeAxis {
    pub name: String,
    pub tol: f64,
    pub can_round: bool,
    pub range: (f64, f64),
    pub type_: Duration,
}

impl PandasTimedeltaDatacubeAxis {
    pub fn new() -> Self {
        Self {
            name: "timedeltaaxis".to_string(),
            tol: 1e-12,
            can_round: false,
            range: (0., 1.),
            type_: Duration::hours(0),
        }
    }
}

impl DatacubeAxis for PandasTimedeltaDatacubeAxis {

    fn parse(&self, value: &dyn Any) -> Box<dyn Any> {
        if let Some(s) = value.downcast_ref::<&str>() {
            // Basic parsing for "60", "60s", "1h"
            let trimmed = s.trim();
            if let Ok(hours) = trimmed.parse::<i64>() {
                return Box::new(Duration::hours(hours));
            } else if let Some(stripped) = trimmed.strip_suffix("s") {
                if let Ok(secs) = stripped.parse::<i64>() {
                    return Box::new(Duration::seconds(secs));
                }
            } else if let Some(stripped) = trimmed.strip_suffix("m") {
                if let Ok(mins) = stripped.parse::<i64>() {
                    return Box::new(Duration::minutes(mins));
                }
            } else if let Some(stripped) = trimmed.strip_suffix("h") {
                if let Ok(hours) = stripped.parse::<i64>() {
                    return Box::new(Duration::hours(hours));
                }
            }
            Box::new("invalid")
        } else if let Some(dur) = value.downcast_ref::<Duration>() {
            Box::new(*dur)
        } else {
            Box::new("invalid")
        }
    }

    fn to_float(&self, value: &dyn std::any::Any) -> Option<f64> {
        if let Some(dur) = value.downcast_ref::<Duration>() {
            Some(dur.num_nanoseconds()? as f64 / 1_000_000_000.0)
        } else {
            None
        }
    }

    fn from_float(&self, value: f64) -> Box<dyn std::any::Any> {
        let secs = value.trunc() as i64;
        let nanos = ((value.fract()) * 1_000_000_000.0).round() as i64;
        let total_nanos = secs * 1_000_000_000 + nanos;
        Box::new(Duration::nanoseconds(total_nanos))
    }

    fn serialize(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        if let Some(dur) = value.downcast_ref::<Duration>() {
            let secs = dur.num_seconds();
            Box::new(format!("{}s", secs))
        } else {
            Box::new("invalid")
        }
    }

    fn offset(&self, value: &dyn Any) -> Option<Box<dyn Any>>{
        None
    }
}


// UnsliceableDatacubeAxis

#[derive(Debug)]
pub struct UnsliceableDatacubeAxis {
    pub name: String,
    pub tol: f64,
    pub can_round: bool,
    pub range: (i32, i32),
    pub type_: f64,
}

impl UnsliceableDatacubeAxis {
    pub fn new() -> Self {
        Self {
            name: "unsliceable_axis".to_string(),
            tol: f64::NAN,
            can_round: false,
            range: (0, 1),
            type_: f64::NAN,
        }
    }
}

impl DatacubeAxis for UnsliceableDatacubeAxis {
    fn parse(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        if let Some(s) = value.downcast_ref::<String>() {
            Box::new(s.clone())
        } else {
            Box::new("invalid")
        }
    }

    fn to_float(&self, value: &dyn std::any::Any) -> Option<f64> {
        None
    }

    fn from_float(&self, value: f64) -> Box<dyn std::any::Any> {
        Box::new("Tried to slice unsliceable axis")
    }

    fn serialize(&self, value: &dyn std::any::Any) -> Box<dyn std::any::Any> {
        Box::new("Tried to slice unsliceable axis")
    }
}


#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum AxisType {
    Int,
    Float,
    Str,
    Timedelta,
    Timestamp,
}

trait IntoAxisType {
    fn into_axis_type(&self) -> AxisType;
}

impl IntoAxisType for i32 {
    fn into_axis_type(&self) -> AxisType { AxisType::Int }
}
impl IntoAxisType for f64 {
    fn into_axis_type(&self) -> AxisType { AxisType::Float }
}
impl IntoAxisType for String {
    fn into_axis_type(&self) -> AxisType { AxisType::Str }
}
impl IntoAxisType for &str {
    fn into_axis_type(&self) -> AxisType { AxisType::Str }
}
impl IntoAxisType for chrono::Duration {
    fn into_axis_type(&self) -> AxisType {AxisType::Timedelta}
}
impl IntoAxisType for chrono::DateTime<Utc> {
    fn into_axis_type(&self) -> AxisType {AxisType::Timestamp}
}

use std::collections::HashMap;

// const type_to_axis_lookup: HashMap<AxisType, Box<dyn DatacubeAxis>> = HashMap::from([
//         (AxisType::Int, Box::new(IntDatacubeAxis::new())),
//         (AxisType::Float, Box::new(FloatDatacubeAxis::new())),
//         (AxisType::Str, Box::new(UnsliceableDatacubeAxis::new())),
//         (AxisType::Timedelta, Box::new(PandasTimedeltaDatacubeAxis::new())),
//         (AxisType::Timestamp, Box::new(PandasTimestampDatacubeAxis::new())),
//     ]);

use once_cell::sync::Lazy;

// static TYPE_TO_AXIS_LOOKUP: Lazy<HashMap<AxisType, Box<dyn DatacubeAxis>>> = Lazy::new(|| {
//     HashMap::from([
//         (AxisType::Int, Box::new(IntDatacubeAxis::new())),
//         (AxisType::Float, Box::new(FloatDatacubeAxis::new())),
//         (AxisType::Str, Box::new(UnsliceableDatacubeAxis::new())),
//         (AxisType::Timedelta, Box::new(PandasTimedeltaDatacubeAxis::new())),
//         (AxisType::Timestamp, Box::new(PandasTimestampDatacubeAxis::new())),
//     ])
// });

// static TYPE_TO_AXIS_LOOKUP: Lazy<
//     HashMap<AxisType, fn() -> Box<dyn DatacubeAxis + Send + Sync>>
// > = Lazy::new(|| {
//     HashMap::from([
//         (AxisType::Int, || Box::new(IntDatacubeAxis::new())),
//         (AxisType::Float, || Box::new(FloatDatacubeAxis::new())),
//         // (AxisType::Str, || Box::new(UnsliceableDatacubeAxis::new())),
//         // (AxisType::Timedelta, || Box::new(PandasTimedeltaDatacubeAxis::new())),
//         // (AxisType::Timestamp, || Box::new(PandasTimestampDatacubeAxis::new())),
//     ])
// });

// fn make_int_axis() -> Box<dyn DatacubeAxis + Send + Sync> {
//     Box::new(IntDatacubeAxis::new())
// }

// fn make_float_axis() -> Box<dyn DatacubeAxis + Send + Sync> {
//     Box::new(FloatDatacubeAxis::new())
// }

// static TYPE_TO_AXIS_LOOKUP: Lazy<
//     HashMap<AxisType, fn() -> Box<dyn DatacubeAxis + Send + Sync>>
// > = Lazy::new(|| {
//     HashMap::from([
//         (AxisType::Int, make_int_axis),
//         (AxisType::Float, make_float_axis),
//     ])
// });

// static TYPE_TO_AXIS_LOOKUP: Lazy<
//     HashMap<AxisType, Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>>
// > = Lazy::new(|| {
//     HashMap::from([
//         (AxisType::Int, Box::new(|| Box::new(IntDatacubeAxis::new()))),
//         (AxisType::Float, Box::new(|| Box::new(FloatDatacubeAxis::new()))),
//     ])
// });

static TYPE_TO_AXIS_LOOKUP: Lazy<
    HashMap<
        AxisType,
        Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>
    >
> = Lazy::new(|| {
    HashMap::from([
        (AxisType::Int, Box::new(|| Box::new(IntDatacubeAxis::new()) as Box<dyn DatacubeAxis + Send + Sync>) as Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>),
        (AxisType::Float, Box::new(|| Box::new(FloatDatacubeAxis::new()) as Box<dyn DatacubeAxis + Send + Sync>) as Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>),
        (AxisType::Str, Box::new(|| Box::new(UnsliceableDatacubeAxis::new()) as Box<dyn DatacubeAxis + Send + Sync>) as Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>),
        (AxisType::Timedelta, Box::new(|| Box::new(PandasTimedeltaDatacubeAxis::new()) as Box<dyn DatacubeAxis + Send + Sync>) as Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>),
        (AxisType::Timestamp, Box::new(|| Box::new(PandasTimestampDatacubeAxis::new()) as Box<dyn DatacubeAxis + Send + Sync>) as Box<dyn Fn() -> Box<dyn DatacubeAxis + Send + Sync> + Send + Sync>),
        ])
});