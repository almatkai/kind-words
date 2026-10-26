//! Test-only executable: deterministic adapter over the REAL SDK pipes.
#[path = "../fixtures/host-extracted/visibility.rs"]
mod visibility;
pub use visibility::set_backend_app_visibility;
#[tokio::main(worker_threads = 2)]
async fn main() {
    if std::env::args().nth(1).as_deref() == Some("--host-contract") {
        println!("{}", visibility::contract().await);
        return;
    }
    let samples: Vec<f64> = std::env::args()
        .skip(1)
        .map(|s| s.parse().unwrap())
        .collect();
    let samples = std::sync::Mutex::new((samples, 0));
    let adapter = tezbar_kind_words::Adapter::with_random(move || {
        let mut state = samples.lock().unwrap();
        let value = state.0.get(state.1).copied().unwrap_or(0.5);
        state.1 += 1;
        Ok(value)
    });
    if let Err(error) = tezbar_extension_sdk::serve(adapter).await {
        eprintln!("Fixture stopped: {error}");
        std::process::exit(1);
    }
}
