#!/usr/bin/env python3
"""Development archive only: empty artifacts, closed inventory, real binary smoke."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,zipfile
from process import Host,result,action,phase_contract_cases
root=Path(__file__).resolve().parents[1];dist=root/'dist';dist.mkdir(exist_ok=True)
package=dist/'kind-words-aarch64-apple-darwin';package.mkdir(exist_ok=True)
def put(source,name):
 dest=package/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
put(root/'target/release/tezbar-kind-words','bin/kind-words');(package/'bin/kind-words').chmod(0o755)
put(root/'assets/extension-icon.png','resources/extension-icon.png')
for p in (root/'data').iterdir():put(p,'resources/data/'+p.name)
for p in ['LICENSE','NOTICE']:put(root/p,p)
for p in (root/'notices').rglob('*'):
 if p.is_file():put(p,str(p.relative_to(root)))
manifest=json.loads((root/'extension.json').read_text());manifest['files']={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*')) if p.is_file() and p.name!='extension.json'}
(package/'extension.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=dist/'kind-words-aarch64-apple-darwin-dev.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(package.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(package)))
extracted=dist/'extracted';extracted.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:z.extractall(extracted)
exe=extracted/'bin/kind-words';exe.chmod(0o755)
m=json.loads((extracted/'extension.json').read_text());assert m['artifacts']=={}
files={str(p.relative_to(extracted)):hashlib.sha256(p.read_bytes()).hexdigest() for p in extracted.rglob('*') if p.is_file() and p.name!='extension.json'}
assert m['files']==files;assert files['resources/extension-icon.png']=='29cfe562818575c1b217778ae3aff55cb646925feffd0d36aed69082f2787776'
with Host(binary=exe) as h:
 v=result(h.open('quick-compliment'));assert v['mode']=='no-view';assert len(h.effects)==1;h.dispose()
with Host(binary=exe) as h:
 rid=h.request('session.open',dict(sessionId='s',commandName='quick-compliment',preferences={},argumentValues={}))
 reverse=h.wait(rid,ack=False);h.reply(reverse,error={'code':'synthetic','message':'synthetic clipboard failure'})
 recovery=result(h.wait(rid));assert recovery['mode']=='view';assert result(h.op('invoke-action',{'actionId':action(recovery,'retry')}))['mode']=='no-view';assert h.effects[0]==h.effects[1];h.dispose()
phase_contract_cases(exe)
report={'target':'aarch64-apple-darwin','developmentOnly':True,'archive':archive.name,'archiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'executableSha256':files['bin/kind-words'],'files':files,'productionSourceHashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'Cargo.toml',root/'Cargo.lock',*sorted((root/'src').glob('*.rs'))]},'smoke':'extracted production executable: real SDK automatic quick-copy; browsing clipboard object then pinned visibility null; null clipboard rejection; non-null/error/timeout/cancel close-only retry and stale Retry rejection; dispose/EOF, synthetic OS producers only'}
(root/'evidence').mkdir(exist_ok=True);(root/'evidence/dev-package.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS native ARM64 dev ZIP inventory and extracted production executable success/error smoke; no installation/publication.')
