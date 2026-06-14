//! Best-effort registration of Squirrel's configured vault in Obsidian's vault
//! registry (`obsidian.json`), so the "Open Vault" affordances deep-link into
//! the *correct* folder.
//!
//! Background: `obsidian://open?path=<dir>` only opens a vault Obsidian already
//! knows about. If the configured vault was never opened in Obsidian, the URI
//! silently falls back to the last-used vault — the user ends up staring at the
//! wrong notes. Adding the folder to `obsidian.json` ahead of the deep-link
//! fixes that without forcing a manual one-time "Open folder as vault" step.

use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::{json, Map, Value};

/// Location of Obsidian's per-user `obsidian.json`. Same relative layout on all
/// three desktop platforms: `<config dir>/obsidian/obsidian.json`
/// (macOS `~/Library/Application Support`, Linux `~/.config`,
/// Windows `%APPDATA%`).
fn config_path() -> Option<PathBuf> {
    Some(dirs::config_dir()?.join("obsidian").join("obsidian.json"))
}

/// Normalize a vault path for comparison/storage: resolve symlinks when the
/// folder exists, else just strip a trailing separator. Obsidian stores real
/// absolute paths with no trailing slash.
fn normalize(path: &str) -> String {
    if let Ok(canon) = std::fs::canonicalize(path) {
        return canon.to_string_lossy().into_owned();
    }
    path.trim_end_matches('/').to_string()
}

/// 16 hex-char id, matching the shape Obsidian uses as vault keys. Uniqueness
/// only needs to hold within this one file; a 64-bit random value is ample.
fn new_id() -> String {
    use rand::RngCore;
    let mut bytes = [0u8; 8];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

/// Ensure `vault_path` is present in Obsidian's registry. Best-effort: returns
/// `Err` only on real IO/parse failures the caller may want to log; a missing
/// Obsidian install (no config dir) is treated as a no-op success.
pub fn ensure_registered(vault_path: &str) -> Result<(), String> {
    let Some(path) = config_path() else {
        return Ok(()); // no config dir → nothing we can do; not an error
    };
    let mut root: Value = match std::fs::read_to_string(&path) {
        Ok(text) => serde_json::from_str(&text).map_err(|e| e.to_string())?,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => json!({}),
        Err(e) => return Err(e.to_string()),
    };
    if !upsert_vault(&mut root, &normalize(vault_path), new_id, now_ms()) {
        return Ok(()); // already present → leave the file untouched
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let text = serde_json::to_string_pretty(&root).map_err(|e| e.to_string())?;
    std::fs::write(&path, text).map_err(|e| e.to_string())
}

/// Pure registry mutation. Adds a `{path, ts, open:false}` entry under a fresh
/// key when no existing vault matches `vault_path`. Returns `true` when the
/// document changed (caller should persist), `false` when already registered.
fn upsert_vault(
    root: &mut Value,
    vault_path: &str,
    mut id: impl FnMut() -> String,
    ts: u64,
) -> bool {
    if !root.is_object() {
        *root = json!({});
    }
    let obj = root.as_object_mut().unwrap();
    let vaults = obj
        .entry("vaults")
        .or_insert_with(|| Value::Object(Map::new()));
    if !vaults.is_object() {
        *vaults = Value::Object(Map::new());
    }
    let vaults = vaults.as_object_mut().unwrap();
    let already = vaults
        .values()
        .any(|v| v.get("path").and_then(Value::as_str) == Some(vault_path));
    if already {
        return false;
    }
    // Avoid an id collision in the unlikely event the random key already exists.
    let mut key = id();
    while vaults.contains_key(&key) {
        key = id();
    }
    vaults.insert(key, json!({ "path": vault_path, "ts": ts, "open": false }));
    true
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn adds_when_missing() {
        let mut root = json!({"vaults": {"k": {"path": "/v/one"}}});
        let changed = upsert_vault(&mut root, "/v/two", || "abc".into(), 42);
        assert!(changed);
        let entry = &root["vaults"]["abc"];
        assert_eq!(entry["path"], "/v/two");
        assert_eq!(entry["ts"], 42);
        assert_eq!(entry["open"], false);
    }

    #[test]
    fn no_op_when_already_registered() {
        let mut root = json!({"vaults": {"k": {"path": "/v/one", "ts": 1, "open": true}}});
        let changed = upsert_vault(&mut root, "/v/one", || "new".into(), 99);
        assert!(!changed);
        // existing entry untouched, no new key added
        assert_eq!(root["vaults"].as_object().unwrap().len(), 1);
        assert_eq!(root["vaults"]["k"]["open"], true);
    }

    #[test]
    fn creates_vaults_map_when_absent() {
        let mut root = json!({});
        assert!(upsert_vault(&mut root, "/v/x", || "id1".into(), 7));
        assert_eq!(root["vaults"]["id1"]["path"], "/v/x");
    }

    #[test]
    fn picks_fresh_key_on_collision() {
        let mut root = json!({"vaults": {"dup": {"path": "/other"}}});
        let mut seq = vec!["dup".to_string(), "fresh".to_string()].into_iter();
        // first id() returns the colliding key, then a fresh one
        let changed = upsert_vault(&mut root, "/v/new", move || seq.next().unwrap(), 5);
        assert!(changed);
        assert_eq!(root["vaults"]["fresh"]["path"], "/v/new");
        assert!(root["vaults"].get("dup").is_some());
    }
}
