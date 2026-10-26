#![allow(dead_code, private_interfaces)]
// Generated only from immutable host source; see qa/host-native.py.
mod before {
    include!("../fixtures/host-extracted/host_before.rs");
}
mod after {
    include!("../fixtures/host-extracted/host_after.rs");
}

#[path = "../fixtures/host-extracted/visibility.rs"]
mod visibility;
pub use visibility::set_backend_app_visibility;
