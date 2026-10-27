# Frozen fixture evidence

The complete host/SDK path, commit and SHA256 inventory is
[evidence/fixtures.json](evidence/fixtures.json). `python3 qa/integrity.py --verify-git`
compares every fixture with `git show` at its exact pin, reading no sibling working
files; ordinary standalone QA checks the frozen hashes. Source V1 fixtures remain
byte-exact to HEAD; upstream and locked Raycast evidence are unchanged.

Round 2 adds `fixtures/host/src-tauri/src/native_core/platform.rs` verbatim from
host commit `ea100cee3f69711de12485ba061950c5fc65258f`, SHA256
`33e6b7ec5b305ee3ffb857985d0483e54891998ff2a51c10f12695b80a1953e6`.
The existing `process_host.rs` fixture routes `host.window.visibility` to
`core:platform:visibility`, whose platform branch returns normal JSON null.
The host's authentic Apache-2.0 license is `fixtures/host/LICENSE`.

`qa/visibility-host.py` generates `fixtures/host-extracted/visibility.rs` from those
actual match arms. Rustfmt changes formatting only; synthetic surrounding types
replace app availability and record the backend visibility call. No Tauri or real
OS action runs. Rust tests exercise both boolean inputs, invalid typed arguments
and app failure. The QA fixture executable executes the same extraction to return
the default response and embeds both original full sources; Python compares them
with the exact frozen fixtures before supplying the default. Clipboard responses
remain an explicitly synthetic producer with the strict object contract. The old
shared acknowledgement mock did not prove the real visibility contract.

Generated extracts are test-only modified source, separate from immutable host
fixtures. `INDEX.sha256` includes both, their generator, license and evidence.
