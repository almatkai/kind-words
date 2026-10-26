#!/usr/bin/env python3
"""Execute extracted real pinned Rust host functions, no app build/working reads."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def extract(s,name):
 pos=s.index('fn '+name+'(');start=s.rfind('\n',0,pos)+1
 brace=s.index('{',pos);depth=1;i=brace+1
 # These selected functions have no braces inside strings/comments that alter balance.
 while depth:
  if s[i]=='{':depth+=1
  elif s[i]=='}':depth-=1
  i+=1
 return s[start:i].replace('pub(super) ','pub ')
for mode,base in [('before',root/'fixtures/host'),('after',root/'.qa/patched-host')]:
 s=(base/'src-tauri/src/native_core/extensions/registry.rs').read_text()
 functions=['slug','collect','installed','installed_command','platform','compatible','icon_path','command_icon_path']
 if mode=='after':functions+=['native_replacement']
 header='''use serde_json::{json,Value};use std::{path::{Path,PathBuf,Component},collections::HashSet};
struct Paths { data_dir: PathBuf }
struct CoreContext {paths: Paths}
type CoreResult=Result<Value,String>;
fn roots(ctx:&CoreContext)->Vec<PathBuf>{vec![ctx.paths.data_dir.clone()]}
fn read_json(p:&Path)->CoreResult{serde_json::from_slice(&std::fs::read(p).map_err(|e|e.to_string())?).map_err(|e|e.to_string())}
fn fallback<'a>(v:&'a Value,key:&str,default:&'a str)->&'a str {v[key].as_str().unwrap_or(default)}
mod process_install {
 use super::*;
 pub struct Package {pub manifest:Value,pub dir:PathBuf}
 // Synthetic stand-in for the verified resolver; only discovery/resource/routing functions are under test.
 pub fn resolve(ctx:&CoreContext,id:&str)->Result<Package,String>{
 let canonical=ctx.paths.data_dir.join(id);let active=canonical.join("versions/synthetic");
 Ok(Package{manifest:read_json(&active.join("extension.json"))?,dir:active})
 }
}
mod v2_runtime {pub fn canonical_id(slug:&str)->String{format!("com.tezbar.native.{slug}")}}
'''
 # actual Installed definition, narrowed visibility only; all fields preserved.
 start=s.index('pub(super) struct Installed');end=s.index('\n}\n',start)+2
 header+=s[start:end].replace('pub(super) ','')+'\n'
 body='\n'.join(extract(s,f) for f in functions)
 # selected source references super::{process_install,v2_runtime}, matching same module siblings.
 content=header+'\nmod actual {use super::*;\n'+body+'\n}\n'
 test='''#[test]fn discovery_resource_and_alias_coverage(){
 let patched=PATCHED;
 let dir=tempfile::tempdir().unwrap();let ctx=CoreContext{paths:Paths{data_dir:dir.path().into()}};
 let canonical=dir.path().join("com.tezbar.native.synthetic");let active=canonical.join("versions/synthetic");std::fs::create_dir_all(active.join("resources")).unwrap();
 std::fs::write(active.join("resources/icon.png"),b"original PNG synthetic stand-in").unwrap();
 let manifest=json!({"id":"com.tezbar.native.synthetic","icon":"resources/icon.png","platforms":["macOS","Windows","Linux"],"replaces":["com.tezbar.synthetic","raycast.synthetic"],"commands":[{"name":"covered","runtime":"rust","platforms":["macOS","Windows","Linux"],"icon":"resources/icon.png"}]});
 std::fs::write(active.join("extension.json"),serde_json::to_vec(&manifest).unwrap()).unwrap();
 let e=actual::installed(&ctx,"com.tezbar.native.synthetic").unwrap();assert_eq!(e.path,canonical);
 assert_eq!(actual::icon_path(&e).is_some(),patched);assert_eq!(actual::command_icon_path(&e,&manifest["commands"][0]).is_some(),patched);
 assert_eq!(actual::installed_command(&ctx,"com.tezbar.synthetic","covered").is_some(),patched);
 assert!(actual::installed_command(&ctx,"com.tezbar.synthetic","uncovered").is_none());
 assert!(actual::installed_command(&ctx,"com.tezbar.synthetic-impostor","covered").is_none());
 assert!(actual::installed_command(&ctx,"raycast.synthetic","covered").is_some());
 assert!(!canonical.join("preferences.json").exists());
}
'''.replace('PATCHED','true' if mode=='after' else 'false')
 # test module must access selected functions: narrow visibility export only for harness.
 for name in functions:content=content.replace('fn '+name+'(', 'pub fn '+name+'(').replace('pub pub fn','pub fn')
 out=root/'fixtures/host-extracted'/('host_'+mode+'.rs');out.parent.mkdir(exist_ok=True);out.write_text(content+test)
print('Prepared actual host function extraction fixtures (resolver and CoreContext synthetic).')
