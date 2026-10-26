#!/usr/bin/env python3
"""Capture authentic license texts from the exact locked/downloaded dependencies."""
from pathlib import Path
import hashlib,json,subprocess,os,shutil
root=Path(__file__).resolve().parents[1];out=root/'notices';out.mkdir(exist_ok=True)
env=dict(os.environ,CARGO_HOME=str(root/'.qa/cargo-home'))
metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--format-version','1','--manifest-path',str(root/'Cargo.toml')],env=env))
items=[]
def capture(kind,name,version,base,origin,license):
 dest=out/kind/(name.replace('/','__')+'-'+version);dest.mkdir(parents=True,exist_ok=True)
 files=[]
 for f in sorted(base.iterdir()):
  if f.is_file() and f.name.lower().startswith(('license','licence','copying','notice','copyright','thirdpartynotice')):
   target=dest/f.name;shutil.copyfile(f,target);files.append({'path':str(target.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 item={'kind':kind,'name':name,'version':version,'origin':origin,'declaredLicense':license,'files':files}
 if not files:item['evidenceGap']='No license text present at the installed package root; metadata declaration is not a substitute grant.'
 items.append(item)
for p in metadata['packages']:
 if p['name']=='tezbar-kind-words':continue
 capture('rust',p['name'],p['version'],Path(p['manifest_path']).parent,p['source'],p['license'])
lock=json.loads((root/'fixtures/source/package-lock.json').read_text())['packages']
base=root/'.qa/v1'
for name,p in lock.items():
 if not name or not (base/name/'package.json').exists():continue
 pkg=json.loads((base/name/'package.json').read_text());capture('javascript',pkg['name'],pkg['version'],base/name,p.get('resolved'),pkg.get('license'))
for name,p in json.loads((root/'qa/package-lock.json').read_text())['packages'].items():
 if not name:continue
 base=root/'.qa/schema';pkg=json.loads((base/name/'package.json').read_text());capture('javascript',pkg['name'],pkg['version'],base/name,p.get('resolved'),pkg.get('license'))
for folder,paths in [('sdk',['LICENSE','NOTICE']),('source',['LICENSE'])]:
 for p in paths:shutil.copyfile(root/'fixtures'/folder/p,out/(folder+'-'+p))
# Full original API declaration is evidence for storeValue and default filtering.
f=root/'fixtures/locked-raycast';f.mkdir(exist_ok=True)
for name in ['package.json','types/index.d.ts']:
 src=root/'.qa/v1/node_modules/@raycast/api'/name;dst=f/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
(out/'dependencies.json').write_text(json.dumps(items,indent=2)+'\n')
print('Captured authentic license evidence:',len(items),'locked Rust and installed JS packages; gaps:',sum('evidenceGap' in p for p in items))
