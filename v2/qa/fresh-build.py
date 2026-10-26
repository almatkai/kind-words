#!/usr/bin/env python3
"""Fresh HTTPS dependency/build isolation for the current production sources."""
from pathlib import Path
import hashlib, json, os, subprocess, tempfile
from process import phase_contract_cases

root = Path(__file__).resolve().parents[1]
base = Path(tempfile.mkdtemp(prefix='round2-fresh-', dir=root / '.qa'))
for name in ['home', 'temp', 'cargo', 'target', 'cache']:
    (base / name).mkdir()
env = dict(os.environ)
env.update(RUSTUP_HOME=env.get('RUSTUP_HOME', str(Path.home() / '.rustup')),
           HOME=str(base / 'home'), TMPDIR=str(base / 'temp'),
           XDG_CACHE_HOME=str(base / 'cache'), CARGO_HOME=str(base / 'cargo'),
           CARGO_TARGET_DIR=str(base / 'target'), GIT_TERMINAL_PROMPT='0',
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
def sources():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [root / 'Cargo.toml', root / 'Cargo.lock', *sorted((root / 'src').glob('*.rs'))]}
before = sources()
command = ['cargo', '+stable', 'build', '--locked', '--release', '--bin', 'tezbar-kind-words']
with (base / 'build.log').open('w') as log:
    subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
assert sources() == before, 'production sources changed during isolated build'
log = (base / 'build.log').read_text()
assert 'Updating git repository `https://github.com/almatkai/tezbar-extension-sdk-rust.git`' in log
binary = base / 'target/release/tezbar-kind-words'
phase_contract_cases(binary)
report = {
    'command': command, 'target': 'aarch64-apple-darwin',
    'newEmptyCargoHomeAndTarget': True, 'httpsSdkFetched': True,
    'sdkRev': 'e955911f0bf5b558f9d3eb5183df0adc95c22af2',
    'productionSourceHashes': before,
    'executableSha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
    'log': str((base / 'build.log').relative_to(root)),
    'smoke': 'actual fresh production SDK pipes: method-specific completion, normal browsing/quick, null clipboard rejection, invalid/error/timeout/cancel close, close-only Retry and stale Retry rejection; synthetic OS producers only'
}
(root / 'evidence/fresh-build.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS fresh empty isolated Cargo home/target HTTPS SDK production release build and phase-contract pipes.')
