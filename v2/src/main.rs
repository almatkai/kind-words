#[tokio::main(worker_threads = 2)]
async fn main() {
    if let Err(error) = tezbar_extension_sdk::serve(tezbar_kind_words::Adapter::default()).await {
        eprintln!("Kind Words protocol stopped: {error}");
        std::process::exit(1);
    }
}
