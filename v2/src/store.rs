//! Only the source List.Dropdown storeValue is persisted. No V1 import authority.
use serde_json::{json, Value};
use std::{
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::Mutex,
};
static STORE: Mutex<()> = Mutex::new(());
const LIMIT: u64 = 16 * 1024;
fn checked(path: &Path) -> Result<(), String> {
    if !path.is_absolute() {
        return Err("Private data path must be absolute".into());
    }
    let mut prefix = PathBuf::new();
    for part in path.components() {
        if matches!(
            part,
            std::path::Component::ParentDir | std::path::Component::CurDir
        ) {
            return Err("Unsafe private data path".into());
        }
        prefix.push(part);
        match std::fs::symlink_metadata(&prefix) {
            Ok(m) if m.file_type().is_symlink() => {
                return Err("Symlink in private store path".into())
            }
            Ok(_) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(_) => return Err("Cannot inspect private store".into()),
        }
    }
    Ok(())
}
fn read(root: &Path) -> Result<Value, String> {
    let path = root.join("kind-words/storage.json");
    checked(&path)?;
    if std::fs::symlink_metadata(&path).is_ok_and(|m| !m.is_file()) {
        return Err("Tone store is not a regular file".into());
    }
    let mut value = json!({});
    match std::fs::File::open(&path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(_) => return Err("Cannot read saved tone".into()),
        Ok(f) => {
            if !f
                .metadata()
                .map_err(|_| "Cannot inspect saved tone")?
                .is_file()
            {
                return Err("Tone store is not a regular file".into());
            }
            let mut bytes = Vec::new();
            f.take(LIMIT + 1)
                .read_to_end(&mut bytes)
                .map_err(|_| "Cannot read saved tone")?;
            if bytes.len() as u64 > LIMIT {
                return Err("Saved tone store exceeds 16 KiB".into());
            }
            value = serde_json::from_slice(&bytes).map_err(|_| "Saved tone store is corrupt")?;
        }
    }
    if !value.is_object() || value.as_object().is_some_and(|o| o.len() > 256) {
        return Err("Invalid saved tone store".into());
    }
    if let Some(own) = value.get("kindWords") {
        if own["version"] != 1
            || !own["tone"]
                .as_str()
                .is_some_and(|s| crate::domain::TONES.contains(&s))
        {
            return Err("Unsupported saved tone schema".into());
        }
    }
    Ok(value)
}
pub fn load(root: &Path) -> Result<String, String> {
    let _guard = STORE.lock().map_err(|_| "Tone store lock failed")?;
    let value = read(root)?;
    Ok(value["kindWords"]["tone"].as_str().unwrap_or("all").into())
}
pub fn save(root: &Path, tone: &str) -> Result<(), String> {
    if !crate::domain::TONES.contains(&tone) {
        return Err("Unknown tone".into());
    }
    let _guard = STORE.lock().map_err(|_| "Tone store lock failed")?;
    let mut value = read(root)?;
    if value.get("kindWords").is_none() {
        value["kindWords"] = json!({"version":1});
    }
    value["kindWords"]["tone"] = json!(tone);
    if value.as_object().is_some_and(|o| o.len() > 256) {
        return Err("Saved tone store exceeds 256 root keys".into());
    }
    let bytes = serde_json::to_vec(&value).map_err(|_| "Cannot encode saved tone")?;
    if bytes.len() as u64 > LIMIT {
        return Err("Saved tone store exceeds 16 KiB".into());
    }
    let dir = root.join("kind-words");
    checked(&dir)?;
    std::fs::create_dir_all(&dir).map_err(|_| "Cannot create private tone store")?;
    checked(&dir.join("storage.json"))?;
    let mut file =
        tempfile::NamedTempFile::new_in(&dir).map_err(|_| "Cannot prepare saved tone")?;
    file.write_all(&bytes)
        .and_then(|_| file.as_file().sync_all())
        .map_err(|_| "Cannot write saved tone")?;
    file.persist(dir.join("storage.json"))
        .map_err(|_| "Cannot replace saved tone")?;
    #[cfg(unix)]
    std::fs::File::open(dir)
        .and_then(|f| f.sync_all())
        .map_err(|_| "Cannot sync saved tone")?;
    Ok(())
}
