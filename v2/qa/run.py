#!/usr/bin/env python3
"""All subprocess homes/temp/caches scoped to ignored clone directories."""
from pathlib import Path
import os,shutil,subprocess
root=Path(__file__).resolve().parents[1];qa=root/'.qa'
for n in ['v1','schema','home','temp','cache']:(qa/n).mkdir(parents=True,exist_ok=True)
env=dict(os.environ)
env.update(RUSTUP_HOME=env.get('RUSTUP_HOME',str(Path.home()/'.rustup')),HOME=str(qa/'home'),TMPDIR=str(qa/'temp'),XDG_CACHE_HOME=str(qa/'cache'),CARGO_HOME=str(qa/'cargo-home'),CARGO_TARGET_DIR=str(root/'target'),npm_config_cache=str(qa/'npm-cache'),npm_config_update_notifier='false')
for p in (root/'fixtures/source').rglob('*'):
 if p.is_file():
  out=qa/'v1'/p.relative_to(root/'fixtures/source');out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
for p in (root/'qa').glob('package*.json'):shutil.copyfile(p,qa/'schema'/p.name)
def run(*args):subprocess.run(args,cwd=root,env=env,check=True)
run('npm','ci','--prefix',str(qa/'v1'),'--ignore-scripts','--no-audit','--no-fund')
run('npm','--prefix',str(qa/'v1'),'test');run('npm','--prefix',str(qa/'v1'),'run','typecheck')
run('npm','ci','--prefix',str(qa/'schema'),'--ignore-scripts','--no-audit','--no-fund')
run('python3','qa/prepare-host-patch.py');run('python3','qa/patch-check.py');run('python3','qa/host-native.py')
run('python3','qa/visibility-host.py')
run('cargo','fmt','--check');run('cargo','+1.85.0','fmt','--check')
for t in ['stable','1.85.0']:
 run('cargo','+'+t,'test','--locked','--all-targets')
 run('cargo','+'+t,'clippy','--locked','--all-targets','--','-D','warnings')
 installed=subprocess.check_output(['rustup','target','list','--installed','--toolchain',t],env=env,text=True).splitlines()
 if 'x86_64-pc-windows-gnu' in installed:
  run('cargo','+'+t,'check','--locked','--all-targets','--target','x86_64-pc-windows-gnu')
 else:print('SKIP Windows GNU check: target not installed for '+t,flush=True)
run('cargo','build','--locked','--all-targets')
for script in ['source-oracle.mjs','schema.mjs','renderer.mjs']:run('node','qa/'+script)
run('python3','qa/process.py')
run('cargo','build','--locked','--release','--bin','tezbar-kind-words')
run('python3','qa/fresh-build.py')
run('python3','qa/package.py');run('python3','qa/integrity.py')
