# Immutable provenance

- Own source: `https://github.com/almatkai/kind-words.git`, fresh fetched `origin/main`
  at `a1bf2ff51f80251e24eaeb6d8602b5a8145d1892`. All 26 tracked source files are
  reproduced byte-exact under `fixtures/source/`, including the original lock,
  tests, metadata screenshots, icon, configuration and literal escaped LICENSE.
- Original upstream: `raycast/extensions` commit
  `6734d85992290066fd31a7f5bee3cca3d3545a1a`, path `extensions/kind-words`.
  The own manifest pins this origin. The exact GitHub directory response is
  `fixtures/upstream-tree.json`. The extension-specific LICENSE URL returned 404;
  the repository-root MIT LICENSE at that same commit was retrieved verbatim.
- Original PNG: [immutable upstream bytes](https://raw.githubusercontent.com/raycast/extensions/6734d85992290066fd31a7f5bee3cca3d3545a1a/extensions/kind-words/assets/extension-icon.png),
  SHA256 `29cfe562818575c1b217778ae3aff55cb646925feffd0d36aed69082f2787776`.
  It is identical to the own source PNG. No conversion or substituted SVG.
  See `evidence/icon.json`; all three commands use this asset.
- SDK: `https://github.com/almatkai/tezbar-extension-sdk-rust.git`, rev
  `e955911f0bf5b558f9d3eb5183df0adc95c22af2`, crate `0.1.1`, MSRV `1.85`.
  Cargo resolves immutable HTTPS Git, never the nearby checkout. Exact SDK API,
  protocol, host-integration documents and implementation/license fixtures came
  from the user's read-only SDK Git database at this revision.
- Host: user's read-only `Tezbar` Git object database, commit
  `ea100cee3f69711de12485ba061950c5fc65258f`. No host remote URL is assumed.
  Exact external-extension docs, schema, Recommended catalog, registry, runtime,
  router/module, typed reverse services, renderer and license fixtures are included.
  Round 2 adds only the exact `src-tauri/src/native_core/platform.rs` Git blob:
  SHA256 `33e6b7ec5b305ee3ffb857985d0483e54891998ff2a51c10f12695b80a1953e6`.
  Its visibility arm returns `Ok(Value::Null)`; the typed reverse router forwards
  that result. `qa/visibility-host.py` executes these extracted actual arms with
  synthetic desktop producers; it does not build or patch the host. Host Apache-2.0
  license evidence is unchanged at `fixtures/host/LICENSE`. See [FIXTURES.md](FIXTURES.md).
  `evidence/fixtures.json` lists every Git path, pin and SHA256. Its host/SDK bytes
  were checked directly with `git show`; normal standalone QA rechecks frozen hashes.
- Original locked `@raycast/api` is `1.104.17`; its full exact type declaration and
  package metadata are at `fixtures/locked-raycast/`. Its documented `storeValue`
  and default filtering semantics guide the finite adaptations in INTEGRATION.md.
  The actual esbuild compiler and original TSX/schema modules run inside the oracle;
  proprietary Raycast framework internals are mocked, not claimed as executed.
- `Cargo.lock`, original npm lock and separate `qa/package-lock.json` close dependency
  versions. `notices/dependencies.json` records authentic installed texts/hashes,
  metadata declarations and seven missing-text gaps. No grant was fabricated for
  `r-efi` 5.3.0/6.0.0, `@raycast/api`, platform esbuild binaries, `filelist` or `jake`.

`INDEX.sha256` inventories the entire Git-visible review tree, including V1,
except itself. Build products, ZIPs, caches, synthetic stores and VM output are
ignored. Generate/verify with `python3 qa/integrity.py`; optional `--verify-git`
rechecks the original local Git databases without reading their working files.
