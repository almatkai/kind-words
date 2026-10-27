use serde_json::{json,Value};use std::{path::{Path,PathBuf,Component},collections::HashSet};
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
struct Installed {
    id: String,
    slug: String,
    path: PathBuf,
    manifest: Value,
    resource_root: PathBuf,
    data_dir: PathBuf,
}

mod actual {use super::*;
pub fn slug(id: &str) -> Result<String, String> {
    let name = id
        .trim()
        .strip_prefix("com.tezbar.native.")
        .or_else(|| id.trim().strip_prefix("raycast."))
        .unwrap_or(id.trim());
    if name.is_empty()
        || name.len() > 200
        || !name.as_bytes()[0].is_ascii_alphanumeric()
        || !name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b))
    {
        return Err("Invalid extension id".into());
    }
    Ok(name.into())
}
pub fn collect(ctx: &CoreContext) -> Vec<Installed> {
    let mut found = Vec::new();
    let mut seen = HashSet::new();
    for root in roots(ctx) {
        let mut paths = if root.join("package.json").is_file() {
            vec![root]
        } else {
            std::fs::read_dir(root)
                .into_iter()
                .flatten()
                .filter_map(Result::ok)
                .map(|e| e.path())
                .collect()
        };
        paths.sort();
        for path in paths {
            let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
                continue;
            };
            let Ok(slug) = slug(name) else { continue };
            let native = name.starts_with("com.tezbar.native.");
            let mut resource_root = path.clone();
            let mut manifest = if native {
                match super::process_install::resolve(ctx, name) {
                    Ok(package) => { resource_root = package.dir; package.manifest },
                    Err(error) => {
                        // A damaged canonical directory is NEVER a Raycast package.
                        let mut value = read_json(&path.join("package.json"))
                            .ok()
                            .filter(Value::is_object)
                            .unwrap_or(json!({"id":name,"title":slug}));
                        value["healthError"] = json!(error);
                        value["commands"] = json!([]);
                        value
                    }
                }
            } else {
                let Ok(value) = read_json(&path.join("package.json")) else {
                    continue;
                };
                value
            };
            if native {
                manifest["id"] = json!(name);
            }
            let id = if native {
                name.to_string()
            } else {
                format!("raycast.{slug}")
            };
            if !manifest.is_object() || !seen.insert(id.to_lowercase()) {
                continue;
            }
            found.push(Installed {
                id,
                slug,
                path,
                manifest,
                resource_root,
                data_dir: ctx.paths.data_dir.clone(),
            });
        }
    }
    found
}
pub fn installed(ctx: &CoreContext, id: &str) -> Result<Installed, String> {
    let wanted = slug(id)?;
    let canonical = id.trim().starts_with("com.tezbar.native.");
    collect(ctx)
        .into_iter()
        .find(|entry| {
            entry.slug == wanted && entry.id.starts_with("com.tezbar.native.") == canonical
        })
        .ok_or_else(|| format!("Extension is not installed: {id}"))
}
pub fn installed_command(ctx: &CoreContext, id: &str, command: &str) -> Option<Installed> {
    let native = if let Some(canonical) = native_replacement(ctx, id, command) {
        installed(ctx, &canonical).ok()
    } else if id.starts_with("raycast.") {
        let slug = slug(id).ok()?;
        let canonical = super::v2_runtime::canonical_id(&slug);
        installed(ctx, &canonical).ok()
    } else if id.starts_with("com.tezbar.native.") {
        installed(ctx, id).ok()
    } else {
        None
    };
    if let Some(extension) = native {
        let active = extension.manifest["healthError"].is_null()
            && extension.manifest["commands"]
                .as_array()?
                .iter()
                .any(|c| c["name"] == command && c["runtime"] == "rust" && compatible(c, true));
        if active {
            return Some(extension);
        }
        if id.starts_with("com.tezbar.native.") {
            return None;
        }
    }
    if id.starts_with("com.tezbar.native.") {
        return None;
    }
    let extension = installed(ctx, id).ok()?;
    (compatible(&extension.manifest, false)
        && extension.manifest["commands"]
            .as_array()
            .into_iter()
            .flatten()
            .any(|cmd| cmd["name"].as_str() == Some(command) && compatible(cmd, true)))
    .then_some(extension)
}
pub fn platform() -> &'static str {
    if cfg!(target_os = "windows") {
        "Windows"
    } else if cfg!(target_os = "linux") {
        "Linux"
    } else {
        "macOS"
    }
}
pub fn compatible(manifest: &Value, command: bool) -> bool {
    if command && manifest.get("platforms").is_none() {
        return true;
    }
    let Some(platforms) = manifest["platforms"]
        .as_array()
        .or_else(|| manifest["tezbar"]["platforms"].as_array())
    else {
        return platform() == "macOS";
    };
    platforms
        .iter()
        .filter_map(Value::as_str)
        .any(|value| match value.to_lowercase().as_str() {
            "macos" | "darwin" | "mac" => platform() == "macOS",
            "windows" | "win32" | "win" => platform() == "Windows",
            "linux" => platform() == "Linux",
            _ => false,
        })
}
pub fn icon_path(extension: &Installed) -> Option<String> {
    let name = fallback(&extension.manifest, "icon", "icon.png");
    if name.starts_with("https://") || name.starts_with("http://") {
        return Some(name.into());
    }
    let relative = Path::new(name.strip_prefix("./").unwrap_or(name));
    if relative
        .components()
        .any(|c| !matches!(c, Component::Normal(_)))
    {
        return None;
    }
    let mut candidates = vec![
        extension.resource_root.join(relative),
        extension.resource_root.join("assets").join(relative),
    ];
    if extension.id.starts_with("com.tezbar.native.") {
        if let Some(packages) = extension.path.parent() {
            if let Some(extensions) = packages.parent() {
                let legacy = extensions.join(&extension.slug);
                candidates.push(legacy.join(relative));
                candidates.push(legacy.join("assets").join(relative));
            }
            let legacy = packages.join(format!("raycast.{}", extension.slug));
            candidates.push(legacy.join(relative));
            candidates.push(legacy.join("assets").join(relative));
        }
    }
    candidates
        .into_iter()
        .find(|p| p.is_file())
        .map(|p| p.to_string_lossy().into())
}
pub fn command_icon_path(extension: &Installed, cmd: &Value) -> Option<String> {
    let name = cmd["icon"].as_str().or_else(|| cmd["iconPath"].as_str())?;
    if name.starts_with("https://") || name.starts_with("http://") {
        return Some(name.into());
    }
    let relative = Path::new(name.strip_prefix("./").unwrap_or(name));
    if relative
        .components()
        .any(|c| !matches!(c, Component::Normal(_)))
    {
        return None;
    }
    let mut candidates = vec![
        extension.resource_root.join(relative),
        extension.resource_root.join("assets").join(relative),
    ];
    if extension.id.starts_with("com.tezbar.native.") {
        if let Some(packages) = extension.path.parent() {
            if let Some(extensions) = packages.parent() {
                let legacy = extensions.join(&extension.slug);
                candidates.push(legacy.join(relative));
                candidates.push(legacy.join("assets").join(relative));
            }
            let legacy = packages.join(format!("raycast.{}", extension.slug));
            candidates.push(legacy.join(relative));
            candidates.push(legacy.join("assets").join(relative));
        }
    }
    candidates
        .into_iter()
        .find(|p| p.is_file())
        .map(|p| p.to_string_lossy().into())
}
pub fn native_replacement(ctx: &CoreContext, id: &str, command: &str) -> Option<String> {
    let mut matches = collect(ctx).into_iter().filter(|e| {
        e.id.starts_with("com.tezbar.native.")
            && e.manifest["healthError"].is_null()
            && e.manifest["replaces"].as_array().is_some_and(|a| a.iter().any(|v| v.as_str() == Some(id)))
            && e.manifest["commands"].as_array().is_some_and(|a| a.iter().any(|c| c["name"] == command && c["runtime"] == "rust" && compatible(c, true)))
    });
    let selected = matches.next()?.id;
    matches.next().is_none().then_some(selected)
}
}
#[test]fn discovery_resource_and_alias_coverage(){
 let patched=true;
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
