# Host integration review

Target host: `ea100cee3f69711de12485ba061950c5fc65258f`.
No working host files were read, changed, built, checked out or staged. All host
reads used `git show <exact-sha>:<path>`. The app remains outside this task.

[host-prerequisites.patch](integration/host-prerequisites.patch) is separate and
**unapplied**. `qa/prepare-host-patch.py` reproduces it from frozen host fixtures.
It contains only surfaces used by this port:

1. Registry icon lookup uses verified active-version `package.dir`; canonical
   `Installed.path` remains the preference/uninstall root. Both extension and
   command icons work without a legacy installation supplying their PNG.
2. Runtime aliases resolve exact `replaces` entries from verified installed
   manifests, only for Rust commands covered on the current platform. Ambiguous,
   damaged, prefix-only and uncovered matches cannot claim a native replacement.
   This covers `com.tezbar.kind-words` and `raycast.kind-words` without catalog edits.
3. List dropdown parsing accepts a controlled `value`, including an empty-string
   All option. Lists honor `selectedItemId` and opt-in `onSelectionActionId` for
   keyboard/hover selection. Row primary clicks invoke just the exact row action.
4. Detail primary clicks wrap the callback so React MouseEvent cannot become an
   action ID. Recovery views use this path.
5. An action returning no-view disposes its session and calls `onBack`, closing
   an otherwise stranded recovery view. Initial no-view launch already disposes.

Actual pinned renderer components/callbacks execute before and after in
`qa/renderer.mjs`; extracted actual Rust discovery/icon/alias functions execute
in `tests/host.rs`. Their resolver/CoreContext and UI/React hook boundaries are
synthetic. `qa/visibility-host.py` also executes the exact frozen
`process_host.rs` visibility arm and `platform.rs` visibility arm with synthetic
app availability and a recording backend visibility producer. Its executed result
supplies the Python host's default visibility response, with full fixture-source
checks against the compiled binary. The previous shared `{ok:true}` mock was
incorrect and did not validate visibility; `QA.md` records that corrected defect.
This is not a full host typecheck/build, DOM render or live GUI test.
No Form or unrelated host feature patches are included.

The source HUD has no corresponding typed immediate HUD service. The port returns
exact `Copied: <source text>` as the protocol message after acknowledgement;
browsing copy then awaits `host.window.visibility {visible:false}`. The two
responses have different pinned contracts: `host.clipboard.write` requires a
closed `{ok:true}` object with optional string `message`; visibility requires
JSON **null**, returned normally by `core:platform:visibility` after the backend
visibility call. No structured visibility acknowledgement is expected. Every
non-null visibility result (including `{ok:true}` or booleans), host error or
5-second timeout retains the Close checkpoint for deliberate close-only Retry.
A later null after cancellation/timeout cannot advance that checkpoint. A fresh
explicit Retry receiving null finishes no-view without another clipboard write.
Quick Copy only writes the clipboard, like its source. Thus the original HUD-before-close
visual timing is a finite adaptation, pending real host acceptance. No settings,
browser, paste, clipboard read or other capabilities are requested.

The original List delegates search behavior to the launcher. This implementation
uses the pinned host's title-only, trimmed case-insensitive substring behavior,
with source order retained, rather than promising Raycast's private fuzzy ranking.
Search text, raw/effective selection and tone remain in the session. The original
raw selected ID is retained when a tone's effective fallback is random, matching
useMemo/exclude behavior until a genuine selection event arrives.

OS randomness supplies 53 bits for `floor(u * candidates.length)` with the exact
original exclusion rule and candidate order. No modulo sampler or production seed
is used, and no claim of an identical nondeterministic production sequence is made.
Only the separate, unshipped QA executable injects deterministic samples.

Authoritative revisions and prepared effect checkpoints live outside the SDK's
staged JSON state. Actions consume their revision before reverse awaits; search
revisions cannot restore earlier action IDs. A pending copy/close requires explicit
Retry, preserving exact prepared bytes and never re-randomizing. An acknowledged
copy followed by failed close retries only close. Timeout, malformed ACK, cancellation
and unknown/late ACK never trigger automatic replay. Cancellation cannot undo an
OS effect. A cancelled **open** is removed by SDK ownership and can lose its prepared
checkpoint; a later fresh launch may choose different text. No hidden persistent
clipboard journal was invented to avoid that source-compatible lifecycle limit.

One SDK-owned inert cleanup guard per session removes adapter registration even
when cancelled opens do not run dispose hooks. There are no detached adapter tasks,
threads, timers, polling loops or background leases; all views use `refreshMs:null`.
The SDK itself owns its documented bounded stdio/task machinery.
