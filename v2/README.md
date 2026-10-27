# Kind Words Rust V2

Development implementation on `feat/native-v2-rust`, prepared for parent review.
Not installed, published, released or added to the host catalog. V1 remains intact
apart from the root README discovery link.

This is an independent Rust process using schema 3 / protocol 1 and immutable
`tezbar-extension-sdk` 0.1.1. It implements all three original commands:

- **Random Compliment:** original 75 records in source order, random preselection,
  all four tones, stored tone dropdown, selected-row detail, Copy Compliment and Shuffle.
- **Quick Compliment:** automatic random copy at launch, with success only after
  host acknowledgement. No additional confirmation screen on a successful run.
- **Gratitude Note:** original 12 prompts, context and every opener example,
  random preselection, selected-row detail, Copy Prompt and Shuffle.

There are no source preferences, arguments, favorites, history or network calls.
Browsing copy requires the clipboard's strict `{ok:true}` acknowledgement, then
the pinned visibility service's **null** completion. Non-null/error/timeout close
results show Retry Close, which only closes and never copies again. Quick Copy
writes once without a close call. The corrected method-specific contract and the
previous QA mock defect are documented in [QA.md](QA.md).

Only the original dropdown's `storeValue` behavior persists, in the SDK-provided
private data directory. V1 data is not imported.

Read [QA.md](QA.md) for executed checks and limits,
[INTEGRATION.md](INTEGRATION.md) for the required **unapplied** generic host patch,
and [PROVENANCE.md](PROVENANCE.md) for exact source/SDK/host/icon evidence.

Build from this directory with `cargo build --locked --release --bin tezbar-kind-words`.
Run `bash qa/run.sh` for isolated QA, including a new empty-Cargo-home HTTPS
production build and extracted dev-package phase-contract smoke. It uses already
installed Rust stable/1.85,
Node/npm and Python, and creates all home/cache/temp/build/archive output inside
ignored `v2/.qa`, `v2/target` and `v2/dist`. Build tools are for development only;
the packaged executable contains no JavaScript runtime or local SDK dependency.
`ci.example.yml` is inactive and publishes nothing.

The ignored ARM64 development ZIP has a complete file inventory and extracted
production-process smoke evidence at [evidence/dev-package.json](evidence/dev-package.json).
Its `artifacts` remains empty: it has no invented release URLs or installation claim.
