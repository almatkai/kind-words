#!/usr/bin/env python3
"""Check immutable fixtures/V1 and close the Git-visible inventory, without staging."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[1];repo=root.parent
SOURCE='a1bf2ff51f80251e24eaeb6d8602b5a8145d1892';HOST='ea100cee3f69711de12485ba061950c5fc65258f';SDK='e955911f0bf5b558f9d3eb5183df0adc95c22af2'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==SOURCE
assert git('branch','--show-current').decode().strip()=='feat/native-v2-rust'
assert not git('diff','--cached','--name-only')
tracked=git('ls-tree','-r','--name-only',SOURCE).decode().splitlines()
for name in tracked:
 original=git('show',SOURCE+':'+name)
 current=(repo/name).read_bytes()
 if name=='README.md':assert current==original+b'\nRust V2 development port and review notes: [v2/README.md](v2/README.md).\n'
 else:assert current==original,name
 assert (root/'fixtures/source'/name).read_bytes()==original,name
fixtures=[]
evidence=root/'evidence/fixtures.json'
if '--verify-git' in sys.argv:
 for kind,source_repo,sha in [('host',repo.parent.parent/'Tezbar',HOST),('sdk',repo.parent/'tezbar-extension-sdk-rust',SDK)]:
  for p in sorted((root/'fixtures'/kind).rglob('*')):
   if not p.is_file():continue
   name=str(p.relative_to(root/'fixtures'/kind))
   original=subprocess.check_output(['git','-C',str(source_repo),'show',sha+':'+name])
   assert p.read_bytes()==original,name
   fixtures.append({'path':str(p.relative_to(root)),'repository': 'user-specified readonly Tezbar Git object database' if kind=='host' else 'https://github.com/almatkai/tezbar-extension-sdk-rust','commit':sha,'gitPath':name,'sha256':hashlib.sha256(original).hexdigest()})
else:
 fixtures=json.loads(evidence.read_text())
 for f in fixtures:
  assert f['commit'] in [HOST,SDK]
  assert hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
# Frozen provenance is independently inspectable; optional sibling Git access is read-only.
(root/'evidence').mkdir(exist_ok=True)
(root/'evidence/fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n')
visible=[n.decode() for n in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if n]
assert all(n in tracked or n.startswith('v2/') for n in visible)
assert not any('/node_modules/' in n or '/target/' in n or n.endswith(('.zip','.pyc')) for n in visible)
index=repo/'v2/INDEX.sha256'
index.write_text(''.join(hashlib.sha256((repo/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in sorted(visible) if name!='v2/INDEX.sha256'))
print('PASS HEAD unchanged, index empty, all V1 bytes except README discovery link unchanged; exact Git host/SDK fixtures and Git-visible SHA256 inventory.')
