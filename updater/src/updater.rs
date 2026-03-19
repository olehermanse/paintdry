use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use crate::config::load_config;
use crate::database::Database;
use crate::module::Module;
use crate::types::{
    Change, Config, Discovery, ModuleRequest, ModuleResponse, Observation, Resource,
    value_to_db_string,
};
use crate::utils::{ensure_folder, now, timestamp};

pub struct Updater {
    database: Database,
    cache: HashMap<String, bool>,
    modules: HashMap<String, Module>,
    module_folders: Arc<Mutex<HashMap<String, String>>>,
    discovery_backlog: Arc<Mutex<Vec<Discovery>>>,
}

/// Process all response JSON files found in registered module folders.
fn process_response_files(
    db: &mut Database,
    module_folders: &Arc<Mutex<HashMap<String, String>>>,
    discovery_backlog: &Arc<Mutex<Vec<Discovery>>>,
) {
    let folders: HashMap<String, String> = module_folders.lock().unwrap().clone();
    for (module_name, folder) in &folders {
        let output_path = Path::new(folder);
        if !output_path.is_dir() {
            continue;
        }
        let entries: Vec<_> = match fs::read_dir(output_path) {
            Ok(rd) => rd
                .filter_map(|e| e.ok())
                .filter(|e| {
                    e.path().is_file()
                        && e.path()
                            .extension()
                            .map_or(false, |ext| ext == "json")
                })
                .collect(),
            Err(_) => continue,
        };
        for entry in entries {
            let path = entry.path();
            let data = fs::read_to_string(&path).unwrap_or_else(|e| {
                eprintln!("Failed to read response file {:?}: {}", path, e);
                "[]".to_string()
            });
            let responses: Vec<serde_json::Value> =
                serde_json::from_str(&data).unwrap_or_else(|e| {
                    eprintln!("Failed to parse response file {:?}: {}", path, e);
                    vec![]
                });
            for response in responses {
                process_single_response(db, module_name, response, discovery_backlog);
            }
            println!(
                "Done processing response, deleting: {}",
                path.display()
            );
            fs::remove_file(&path).ok();
        }
    }
}

/// Process a single parsed module response: upsert observations/resources/changes,
/// push cross-module discoveries to the shared backlog.
fn process_single_response(
    db: &mut Database,
    module_name: &str,
    response: serde_json::Value,
    discovery_backlog: &Arc<Mutex<Vec<Discovery>>>,
) {
    let resp: ModuleResponse = match serde_json::from_value(response) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("Failed to parse module response: {}", e);
            return;
        }
    };

    match resp.operation.as_str() {
        "observation" => {
            let value_str = match &resp.value {
                Some(v) => value_to_db_string(v),
                None => String::new(),
            };
            let attribute = resp.attribute.unwrap_or_default();
            println!(
                "Observation: {} {} = {} ({})",
                resp.resource, attribute, value_str, resp.module
            );
            let ts = chrono::DateTime::from_timestamp(resp.timestamp, 0)
                .unwrap_or_else(chrono::Utc::now)
                .naive_utc();
            let obs = Observation {
                resource: resp.resource,
                module: resp.module,
                attribute,
                value: value_str,
                timestamp: ts,
                severity: resp.severity.unwrap_or_default(),
            };
            db.upsert_observation(&obs);
        }
        "discovery" => {
            let discovery = Discovery {
                resource: resp.resource,
                module: resp.module,
                source: resp.source.unwrap_or_default(),
            };
            if discovery.module != module_name {
                println!(
                    "Discovery: {} for {} suggested by {}",
                    discovery.resource, discovery.module, module_name
                );
                discovery_backlog.lock().unwrap().push(discovery);
            } else {
                println!(
                    "Discovery: {} accepted by {}",
                    discovery.resource, module_name
                );
                let resource = Resource::from_discovery(&discovery);
                db.upsert_resource(&resource, &discovery.source);
            }
        }
        "change" => {
            let change = Change {
                resource: resp.resource,
                module: resp.module,
                attribute: resp.attribute.unwrap_or_default(),
                old_value: resp
                    .old_value
                    .map(|v| value_to_db_string(&v))
                    .unwrap_or_default(),
                new_value: resp
                    .new_value
                    .map(|v| value_to_db_string(&v))
                    .unwrap_or_default(),
                severity: resp.severity.unwrap_or_default(),
                timestamp: resp.timestamp,
            };
            db.update_change(&change);
        }
        other => {
            eprintln!("Unknown operation: {}", other);
        }
    }
}

impl Updater {
    pub fn new() -> Self {
        let module_folders: Arc<Mutex<HashMap<String, String>>> =
            Arc::new(Mutex::new(HashMap::new()));
        let discovery_backlog: Arc<Mutex<Vec<Discovery>>> = Arc::new(Mutex::new(Vec::new()));

        // Spawn background thread for continuous response processing
        let bg_folders = Arc::clone(&module_folders);
        let bg_backlog = Arc::clone(&discovery_backlog);
        thread::spawn(move || {
            let mut db = Database::new();
            loop {
                process_response_files(&mut db, &bg_folders, &bg_backlog);
                thread::sleep(Duration::from_secs(5));
            }
        });

        Self {
            database: Database::new(),
            cache: HashMap::new(),
            modules: HashMap::new(),
            module_folders,
            discovery_backlog,
        }
    }

    fn get_or_create_module(&mut self, name: &str, config: &Config) -> bool {
        if self.modules.contains_key(name) {
            return true;
        }
        if let Some(mod_config) = config.modules.get(name) {
            let module = Module::new(name, &mod_config.command, mod_config.slow);
            self.module_folders
                .lock()
                .unwrap()
                .insert(name.to_string(), module.output_folder().to_string());
            self.modules.insert(name.to_string(), module);
            true
        } else {
            println!("Warning: Module '{}' missing", name);
            false
        }
    }

    fn process_discovery_backlog(&mut self, config: &Config) {
        println!("Processing discovery backlog");
        let backlog: Vec<Discovery> = self.discovery_backlog.lock().unwrap().drain(..).collect();
        let mut per_module: HashMap<String, Vec<ModuleRequest>> = HashMap::new();

        for discovery in &backlog {
            let request = ModuleRequest::discovery(
                &discovery.resource,
                &discovery.module,
                &discovery.source,
                now(),
            );
            per_module
                .entry(discovery.module.clone())
                .or_default()
                .push(request);
        }

        for (name, requests) in per_module {
            if !self.get_or_create_module(&name, config) {
                continue;
            }
            if let Some(module) = self.modules.get_mut(&name) {
                module.write_requests(&requests);
            }
        }
    }

    fn send_request_for_resource(&mut self, resource: &Resource, module_name: &str) {
        println!(
            "Sending requests to '{}' module for '{}'",
            module_name, resource.resource
        );
        let source = resource.source.as_deref().unwrap_or("");
        let ts = now();
        let requests = vec![
            ModuleRequest::discovery(&resource.resource, module_name, source, ts),
            ModuleRequest::observation(&resource.resource, module_name, ts),
        ];
        if let Some(module) = self.modules.get_mut(module_name) {
            module.send_requests(requests);
        }
        println!(
            "Sent requests to '{}' module for '{}'",
            module_name, resource.resource
        );
    }

    fn initiate_requests(&mut self, resource: &Resource) {
        let key = format!("{} - {}", resource.module, resource.resource);
        if self.cache.contains_key(&key) {
            return;
        }
        self.cache.insert(key, true);

        let config = load_config();
        let module_name = resource.module.clone();
        if !self.get_or_create_module(&module_name, &config) {
            eprintln!("Target '{}' not supported!", module_name);
            return;
        }
        // Clone what we need to avoid borrow issues
        let res = Resource {
            resource: resource.resource.clone(),
            module: resource.module.clone(),
            source: resource.source.clone(),
        };
        self.send_request_for_resource(&res, &module_name);
    }

    fn process_config_target(&mut self, resource: &str, module_name: &str) {
        let request =
            ModuleRequest::discovery(resource, module_name, "config.json", now());
        if let Some(module) = self.modules.get_mut(module_name) {
            module.send_requests(vec![request]);
        }
    }

    fn setup_requests(&mut self) {
        let resources = self.database.get_resources();
        for resource in resources {
            self.initiate_requests(&resource);
        }
    }

    fn process_changes(&mut self, config: &Config) {
        let changes = self.database.get_new_changes();
        if changes.is_empty() {
            println!("No new changes...");
            return;
        }
        println!("Processing {} new change(s):", changes.len());

        let mut per_module: HashMap<String, Vec<ModuleRequest>> = HashMap::new();
        for change in &changes {
            let request = change.to_request();
            per_module
                .entry(change.module.clone())
                .or_default()
                .push(request);
        }

        for (name, requests) in per_module {
            if !self.get_or_create_module(&name, config) {
                continue;
            }
            if let Some(module) = self.modules.get_mut(&name) {
                module.send_requests(requests);
                module.start();
            }
        }
        println!("Done processing {} new change(s).", changes.len());
    }

    fn wait_modules(&mut self) {
        for module in self.modules.values_mut() {
            module.wait();
        }
    }

    pub fn update(&mut self) {
        let config = load_config();

        // Setup state
        ensure_folder("./state");
        let metadata_path = "state/metadata.json";
        let metadata = load_metadata(metadata_path);

        // Setup snapshots
        let snapshots_dir = ensure_folder("./state/snapshots");

        // Prepare next snapshot
        let time = timestamp();
        let seq = metadata.last_seq + 1;
        let snapshot_name = format!("{:05}-{}", seq, time);
        let snapshot_dir = format!("{}/{}", snapshots_dir, snapshot_name);
        ensure_folder(&snapshot_dir);

        // Start modules, letting them process pre-existing request files
        let module_names: Vec<String> = config.modules.keys().cloned().collect();
        for name in &module_names {
            self.get_or_create_module(name, &config);
            if let Some(module) = self.modules.get_mut(name) {
                module.start();
            }
        }

        // Send change requests
        self.process_changes(&config);

        // Send requests based on config.json targets
        for target in &config.targets {
            for module_name in &target.modules {
                self.get_or_create_module(module_name, &config);
                for resource in &target.resources {
                    println!("Processing config: {} {}", module_name, resource);
                    self.process_config_target(resource, module_name);
                }
            }
        }

        // Send requests based on resources table
        self.setup_requests();
        for name in &module_names {
            if let Some(module) = self.modules.get_mut(name) {
                module.start();
            }
        }

        // Wait for subprocesses to finish (response files processed by background thread)
        self.wait_modules();

        // Process cross-module discoveries
        self.process_discovery_backlog(&config);

        // Send change requests again
        self.process_changes(&config);

        // Commit snapshot
        save_metadata(metadata_path, &time, &snapshot_name, seq);
        let snapshot_metadata = format!("{}/metadata.json", snapshot_dir);
        save_metadata(&snapshot_metadata, &time, &snapshot_name, seq);
    }
}

struct Metadata {
    last_seq: u64,
}

fn load_metadata(path: &str) -> Metadata {
    if let Ok(data) = std::fs::read_to_string(path) {
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(&data) {
            if let Some(last_update) = val.get("last_update") {
                if let Some(seq) = last_update.get("seq").and_then(|s| s.as_u64()) {
                    return Metadata { last_seq: seq };
                }
            }
        }
    }
    Metadata { last_seq: 0 }
}

fn save_metadata(path: &str, time: &str, snapshot_name: &str, seq: u64) {
    let data = serde_json::json!({
        "last_update": {
            "time": time,
            "name": snapshot_name,
            "seq": seq,
        }
    });
    let content = serde_json::to_string_pretty(&data).unwrap() + "\n";
    std::fs::write(path, content).unwrap_or_else(|e| {
        eprintln!("Failed to write metadata '{}': {}", path, e);
    });
}
