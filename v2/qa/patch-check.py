#!/usr/bin/env python3
"""Apply prerequisite patch ONLY to an ignored frozen-fixture copy, never the app."""
from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];repo=root.parent
source=root/'fixtures/host';dest=root/'.qa/host-patch-check'
shutil.copytree(source,dest,dirs_exist_ok=True)
patch=root/'integration/host-prerequisites.patch';relative=str(dest.relative_to(repo))
for check in [True,False]:
 args=['git','-C',str(repo),'apply','--directory='+relative]
 if check:args.append('--check')
 subprocess.run([*args,str(patch)],check=True)
for p in (root/'.qa/patched-host').rglob('*'):
 if p.is_file():assert p.read_bytes()==(dest/p.relative_to(root/'.qa/patched-host')).read_bytes(),p
print('PASS prerequisite patch applies cleanly to frozen-fixture copy and exactly matches tested patched sources; real host remains untouched.')
