use std::mem;

pub fn divide(a: i32, b: i32) -> i32 {
    let opt: Option<i32> = Some(a / b);
    let value = opt.unwrap();
    let other = opt.expect("must have value");

    let raw: u32 = unsafe { mem::transmute::<f32, u32>(1.0_f32) };
    println!("value={}, other={}, raw={}", value, other, raw);
    dbg!(value);

    if b == 0 {
        panic!("div by zero");
    }
    value
}
