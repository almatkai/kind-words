#!/usr/bin/env python3
"""Generate a narrow unapplied prerequisite patch from pinned host snapshots only."""
from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[1];src=root/'fixtures/host';dst=root/'.qa/patched-host'
paths=['src-tauri/src/native_core/extensions/registry.rs','src-tauri/src/native_core/extensions/native.rs','src/renderer/src/raycast-api/list-runtime.tsx','src/renderer/src/raycast-api/detail-runtime.tsx','src/renderer/ExtensionRuntimeView.tsx']
patch=[]
for p in paths:
 old=(src/p).read_text();s=old
 if p.endswith('registry.rs'):
  s=s.replace('    manifest: Value,\n    data_dir:', '    manifest: Value,\n    resource_root: PathBuf,\n    data_dir:',1)
  s=s.replace('            let mut manifest = if native {','            let mut resource_root = path.clone();\n            let mut manifest = if native {',1)
  s=s.replace('Ok(package) => package.manifest,','Ok(package) => { resource_root = package.dir; package.manifest },',1)
  s=s.replace('                manifest,\n                data_dir:', '                manifest,\n                resource_root,\n                data_dir:',1)
  s=s.replace('        path,\n        manifest: Value::Null,','        resource_root: path.clone(),\n        path,\n        manifest: Value::Null,',1)
  # Resource resolution only; canonical path still owns prefs/uninstall.
  s=s.replace('extension.path.join(relative)','extension.resource_root.join(relative)').replace('extension.path.join("assets").join(relative)','extension.resource_root.join("assets").join(relative)')
  insert='''/// Exact replacements are accepted only from verified installed manifests and
/// only for commands actually covered on this platform. No slug guessing.
pub(super) fn native_replacement(ctx: &CoreContext, id: &str, command: &str) -> Option<String> {
    let mut matches = collect(ctx).into_iter().filter(|e| {
        e.id.starts_with("com.tezbar.native.")
            && e.manifest["healthError"].is_null()
            && e.manifest["replaces"].as_array().is_some_and(|a| a.iter().any(|v| v.as_str() == Some(id)))
            && e.manifest["commands"].as_array().is_some_and(|a| a.iter().any(|c| c["name"] == command && c["runtime"] == "rust" && compatible(c, true)))
    });
    let selected = matches.next()?.id;
    matches.next().is_none().then_some(selected)
}

'''
  s=s.replace('/// Native implementations use the same discovery',insert+'/// Native implementations use the same discovery',1)
  # Reuse generic resolver also for installed_command callers.
  s=s.replace('    let native = if id.starts_with("raycast.") {','    let native = if let Some(canonical) = native_replacement(ctx, id, command) {\n        installed(ctx, &canonical).ok()\n    } else if id.starts_with("raycast.") {',1)
 elif p.endswith('native.rs'):
  s=s.replace('if requested.starts_with("com.tezbar.native.") || v2_runtime::slug(requested).is_some()','if requested.starts_with("com.tezbar.native.") || v2_runtime::slug(requested).is_some() || registry::native_replacement(ctx, requested, body["commandName"].as_str().unwrap_or("")).is_some()',1)
  s=s.replace('let canonical = if requested.starts_with("com.tezbar.native.") {','let canonical = if let Some(canonical) = registry::native_replacement(ctx, requested, command) {\n            canonical\n        } else if requested.starts_with("com.tezbar.native.") {',1)
 elif p.endswith('list-runtime.tsx'):
  s=s.replace('type ListAccessory = {','type ListAccessory = {\n  value?: string',1)
  s=s.replace('    actionId: typeof node.props?.actionId',"    value: typeof node.props?.value === 'string' ? node.props.value : undefined,\n    actionId: typeof node.props?.actionId",1)
  s=s.replace("searchAccessory?.options[0]?.value ?? '',","searchAccessory?.value ?? searchAccessory?.options[0]?.value ?? '',",1)
  s=s.replace("      if (!searchAccessory || searchAccessory.options.length === 0) return ''","      if (!searchAccessory || searchAccessory.options.length === 0) return ''\n      if (searchAccessory.value !== undefined && searchAccessory.options.some((option) => option.value === searchAccessory.value)) return searchAccessory.value",1)
  # Selection callback only for packages explicitly declaring the generic opt-in prop.
  marker='  const groupedSections = useMemo'
  s=s.replace(marker,'''  useEffect(() => {
    const requested = root.props?.selectedItemId
    if (typeof requested !== 'string') return
    const index = filteredRows.findIndex((row) => row.id === requested)
    if (index >= 0) setSelected(index)
  }, [root.props?.selectedItemId, filteredRows])

  const selectRow = (index: number): void => {
    setSelected(index)
    const row = filteredRows[index]
    const actionId = root.props?.onSelectionActionId
    if (row && row.id !== root.props?.selectedItemId && typeof actionId === 'string') {
      onRunPrimaryAction(actionId, { value: row.id })
    }
  }

'''+marker,1)
  s=s.replace('      setSelected(next)','      selectRow(next)',1)
  s=s.replace('      setSelected((i) => Math.max(i - 1, 0))','      selectRow(Math.max(selected - 1, 0))',1)
  s=s.replace('onMouseEnter={() => setSelected(globalIdx)}','onMouseEnter={() => selectRow(globalIdx)}',1)
  # Click already invokes the exact row action; don't send an extra selection call
  # that would invalidate that action's revision before clipboard dispatch.
 elif p.endswith('detail-runtime.tsx'):
  s=s.replace('onClick={onRunPrimaryAction}','onClick={() => onRunPrimaryAction()}',1)
 elif p.endswith('ExtensionRuntimeView.tsx'):
  # Only the action result needs this: no-view launch already disposes in host.
  oldblock='''              if (result.mode === 'no-view') {
                setState((prev) => ({ ...prev, message: undefined }))
                return
              }'''
  newblock='''              if (result.mode === 'no-view') {
                await window.tezbar.extensionDisposeSession({ sessionId: state.sessionId })
                if (currentSession.current === sessionOwner) onBack()
                return
              }'''
  assert oldblock in s;s=s.replace(oldblock,newblock,1)
 assert s!=old,p
 out=dst/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s)
 patch.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/'+p,tofile='b/'+p))
out=root/'integration/host-prerequisites.patch';out.parent.mkdir(exist_ok=True);out.write_text(''.join(patch))
print('Generated unapplied host prerequisite patch from exact ea100cee snapshots.')
