// Sample Rust source for the custom policy module.
//
// Build target:
//   wasm32-unknown-unknown
//
// Policy:
//   - Return 1 (allow) when confidence >= 0.5
//   - Return 0 (reject) otherwise

#[no_mangle]
pub extern "C" fn evaluate() -> i32 {
    // In a real module this would read confidence from host-provided context.
    // The checked-in demo .wasm encodes the policy return path directly.
    1
}
