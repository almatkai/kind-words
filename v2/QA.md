# Executed validation and limits

Review date: 2026-10-26, native Apple Silicon macOS. No commit, push, PR, install,
release, catalog change or clone deletion. Source HEAD remains
`a1bf2ff51f80251e24eaeb6d8602b5a8145d1892`; index is empty.

Run `bash qa/run.sh` to reproduce the primary suite from this standalone repository.
It creates disposable exact-lock V1 and QA dependency copies under `.qa/`. All
subprocess homes/temp/cache and package test stores are synthetic and inside the
ignored clone. The product contains only Rust and the immutable Git SDK.

Round 2 corrected a test defect: the old Python `reply(result=None)` converted
explicit null to `{ok:true}`, and auto-replied that object to both reverse methods.
Those earlier passing tests did **not** prove the pinned visibility contract. The
adapter also incorrectly validated close with the clipboard object validator.
Now an omitted-result sentinel selects method-specific defaults; explicit `None`
serializes as JSON null. Clipboard remains strict `{ok:true}` with an optional
string `message` and no other keys. Visibility accepts **only null**, the normal
completion of this exact host revision; `{ok:true}`, booleans, unknown objects and
all other non-null results fail close. Errors and timeouts also fail close.

`qa/visibility-host.py` extracts the actual pinned router and platform match arms,
compiles and executes them with only the desktop app/visibility producer replaced
by a recording mock. The test executable emits the resulting default plus both
full `include_str!` sources; Python checks those bytes against the frozen Git
fixtures before using the visibility default. This detects an old fixture binary.
No new acknowledgement object or visibility host patch was introduced.

Executed checks after the production fix:

- Fresh isolated Cargo home downloaded the SDK over pinned HTTPS Git; native build
  passed without sibling SDK/app/Tauri dependencies. `Cargo.lock` is included.
- Stable and installed **1.85.0**: all-target tests, format check and Clippy with
  `-D warnings` passed. Seven distinct Rust domain/host tests cover complete parsed
  corpora,
  source floor/exclusion/random bounds, strict clipboard ACK, null-only visibility,
  actual extracted visibility routing/platform completion and pinned host
  discovery/icon/routing logic before/after the prerequisite patch. The visibility
  extract test also runs in the QA binary target: eight executions per toolchain.
- Original package's `npm test` (one declared smoke test) and `npm run typecheck`
  passed in a disposable copy using its exact unchanged lock. The separate `tests/`
  Vitest files are frozen evidence; V1 does not declare/install Vitest or run those
  suites through its test script. Their schema functions are directly exercised by
  the closed VM oracle instead.
- Actual original TSX/TS, validators and JSON executed in a closed VM with injected
  random samples and hook state. **164 cases** compare against the deterministic
  Rust adapter over real SDK pipes: every one of 75 compliments and 12 prompts,
  all original fields/order/Unicode/markdown/copy text, actions, default and all tone
  options, selected-row changes, source shuffle exclusion, and automatic Quick Copy.
  Hook/launcher APIs are synthetic; unmocked imports, filesystem, process, OS,
  timers, network, clipboard, browser and settings effects are unavailable in the VM.
- Real SDK JSONL initialization/open/call/search/action/dispose/EOF, source cases,
  latest search and A-B-A stale-action rejection, no-view completion without replay,
  oversized input with reachable Retry, malformed/contradictory ACK, explicit exact
  copy retry, acknowledged-copy/failed-close retry, real 5-second timeout,
  cancellation at copy and close, late responses, and **140 cancelled opens** followed by
  a new successful open, plus explicit 128-session saturation/recovery passed. The product metadata switches are not domain QA.
- Tone persistence: private atomic replacement, unchanged unrelated keys, restart
  restoration, profile isolation, corrupt/unknown-schema/oversized/symlink rejection,
  failed load retry and retained failed tone input retry passed. No V1 migration,
  user profile, real clipboard data, favorite/history store or telemetry was used.
- Exact pinned Draft 2020-12 schema validated the manifest and rejected ten negative
  manifests. Actual pinned Recommended row matches the own repository and all three
  commands. Source artifacts remain `{}`.
- Actual pinned renderer component callbacks run before and after the unapplied
  patch: controlled dropdown restoration/empty All, random selected row, selection,
  exact primary click, Detail MouseEvent wrapper, and no-view disposal/onBack pass.
  Another 26 query cases execute the unmodified pinned renderer default filter
  and match Rust pipes, including case/space/punctuation/Unicode/context exclusion
  and original order. Rust host extracts use synthetic CoreContext and verified-resolver boundary.
  The patch also applied cleanly to an ignored frozen-fixture copy; its results
  exactly matched the tested patched sources. It was not applied to the host.
- Windows GNU `cargo check --locked --all-targets --target x86_64-pc-windows-gnu`
  passed again on stable and 1.85.0 using already installed targets. Earlier MSVC
  was attempted
  and failed with E0463 because `x86_64-pc-windows-msvc` is not installed. No tools
  or targets were installed. Neither check is a linked Windows executable or OS run.
- Native ARM64 release dev ZIP has a closed SHA256 inventory. Every extracted file
  and original PNG hash was verified. The extracted **production executable**
  performed real SDK automatic Quick Copy success and host-error/exact-retry smoke,
  plus both browsing copy flows with clipboard `{ok:true}` then visibility null.
  Null clipboard fails without closing; ten non-null visibility values, host error,
  real 5-second close timeout/late null and cancellation after acknowledged copy
  retain Close. Explicit Retry sends only visibility and null finishes no-view;
  repeated/stale Retry cannot replay clipboard or close. Quick Copy never closes.
  The same phase cases passed on the deterministic SDK fixture and the separate
  fresh-build production executable. All OS producers remain synthetic.
  `evidence/dev-package.json` records archive,
  executable, current production source hashes and all member hashes.
  Archives/executables stay ignored.
- `qa/fresh-build.py` created a new empty Cargo home and target after this
  production change, downloaded the immutable SDK through HTTPS, built the release
  executable and ran the phase cases against that new executable. Current source
  hashes, executable hash, pin and ignored build-log path are recorded in
  `evidence/fresh-build.json`; no old release binary supplies this result.
- V1 tracked-file bytes were compared to exact HEAD; only the short root README
  discovery link differs. SDK/host fixtures were verified against exact Git blobs.
  Git-visible `INDEX.sha256` covers all review sources/fixtures/notices, except itself.
- Initial XERJ autoindex used canonical-root prefix `ax-cf1ee16196c0` and own
  `.git/xerj-state`; 12/12 code files indexed, 20 total indexed, four junk/skipped
  files, exit 3 completed-with-junk. Coverage was incomplete for non-code assets;
  exact source reads/Git/byte checks supplied coverage. No alternate prefix, server
  restart or global search configuration mutation was used. The final update
  aborted with frozen dataset/schema evolution at `v2/Cargo.toml` (exit 1), so the
  new V2 search index is **incomplete/stale**. The requested prefix was retained;
  exact filesystem/Git reads, byte inventories and executable tests verified V2.

Bounds: 128 SDK/adapter sessions, SDK handler/reverse/frame limits, at most 256
bundled records, 4096-byte search, 512-byte action ID, 256-byte session ID, checked
u64 revisions, 16 KiB private JSON and 256 root keys. Host command timeout is 10s;
each effect response deadline is 5s. Clipboard success is a strict object ACK;
visibility success is the pinned null completion. No partial/truncated result is
reported as success.
Filesystem operations are small and synchronous; these logical size bounds do not
promise a hard deadline against a stalled filesystem. Persistent path guards reject
symlinks; they are not an OS sandbox against a concurrently malicious local writer.

Remaining acceptance work: the prerequisite patch is unapplied. Full host build,
DOM rendering, real GUI/clipboard/HUD/focus behavior, linked MSVC build, Windows OS
execution, notarization/signing, production artifact publication/catalog pins and
installation were **not run**. Native source behavior is tested through mocks; the
private Raycast search ranking and original immediate HUD timing are documented
finite adaptations. Cancellation cannot undo a completed effect, and cancelled
opens may lose their prepared retry checkpoint. License-text gaps remain explicit.
