use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

pub fn now() -> i64 {
    chrono::Utc::now().timestamp()
}

pub fn timestamp() -> String {
    chrono::Local::now().format("%Y-%m-%dT%H:%M:%S").to_string()
}

pub fn sha256(data: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn ensure_folder(path: &str) -> String {
    let p = Path::new(path);
    if p.is_dir() {
        return path.to_string();
    }
    if p.exists() {
        eprintln!("'{}' must be a folder", path);
        std::process::exit(1);
    }
    fs::create_dir(p).unwrap_or_else(|e| {
        eprintln!("Failed to create directory '{}': {}", path, e);
        std::process::exit(1);
    });
    path.to_string()
}

pub fn dump_json_atomic(filename: &str, data: &serde_json::Value) {
    let string = serde_json::to_string(data).unwrap() + "\n";
    let tmpfile = format!("{}.tmp", filename);
    fs::write(&tmpfile, &string).unwrap_or_else(|e| {
        eprintln!("Failed to write '{}': {}", tmpfile, e);
    });
    fs::rename(&tmpfile, filename).unwrap_or_else(|e| {
        eprintln!("Failed to rename '{}' to '{}': {}", tmpfile, filename, e);
    });
}
