//! Clean Rust fixture: idiomatic Result-based error handling, no unsafe, no panics.

use std::num::ParseIntError;

pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

pub fn parse_and_double(s: &str) -> Result<i32, ParseIntError> {
    let n: i32 = s.parse()?;
    Ok(n * 2)
}
