use std::path::Path;

use crate::types::Config;

pub fn get_config_filename() -> &'static str {
    if Path::new("./config/config-override.json").is_file() {
        "./config/config-override.json"
    } else {
        "./config/config.json"
    }
}

pub fn load_config() -> Config {
    let filename = get_config_filename();
    let data = std::fs::read_to_string(filename)
        .unwrap_or_else(|e| panic!("Failed to read config '{}': {}", filename, e));
    serde_json::from_str(&data)
        .unwrap_or_else(|e| panic!("Failed to parse config '{}': {}", filename, e))
}
