mod config;
mod database;
mod module;
mod types;
mod updater;
mod utils;

use std::fs;
use std::path::Path;
use std::process::Command;
use std::thread;
use std::time::Duration;

/// Clean up old module request/response JSON files.
fn cleanup_module_files() {
    let modules_dir = Path::new("/paintdry/mount-state/modules/");
    if !modules_dir.is_dir() {
        return;
    }
    fn remove_json_files(dir: &Path) {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    remove_json_files(&path);
                } else if path.extension().map_or(false, |ext| ext == "json") {
                    fs::remove_file(&path).ok();
                }
            }
        }
    }
    remove_json_files(modules_dir);
}

/// Apply database schema, retrying until the database is ready.
fn apply_schema() {
    println!("Waiting for database to be ready and applying schema...");
    loop {
        let status = Command::new("psql").arg("-f").arg("schema.sql").status();
        match status {
            Ok(s) if s.success() => {
                println!("Schema successfully applied!");
                return;
            }
            _ => {
                println!("Schema application failed, retrying in 5 seconds...");
                thread::sleep(Duration::from_secs(5));
            }
        }
    }
}

/// Print debug info from the database tables.
fn print_debug_tables() {
    for table in &["resources", "observations", "history", "changes"] {
        let query = format!("SELECT * FROM {} LIMIT 5;", table);
        println!("{}", query);
        Command::new("psql")
            .arg("-c")
            .arg(&query)
            .status()
            .ok();
    }
}

fn main() {
    cleanup_module_files();
    apply_schema();

    loop {
        print_debug_tables();

        let mut u = updater::Updater::new();
        u.update();

        println!("Sleeping for 60 seconds...");
        thread::sleep(Duration::from_secs(60));
        println!("Updater waking up");
    }
}
