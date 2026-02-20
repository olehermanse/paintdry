use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleRequest {
    pub operation: String,
    pub resource: String,
    pub module: String,
    pub timestamp: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub attribute: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub old_value: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub new_value: Option<String>,
}

impl ModuleRequest {
    pub fn discovery(resource: &str, module: &str, source: &str, timestamp: i64) -> Self {
        Self {
            operation: "discovery".to_string(),
            resource: resource.to_string(),
            module: module.to_string(),
            timestamp,
            source: Some(source.to_string()),
            attribute: None,
            old_value: None,
            new_value: None,
        }
    }

    pub fn observation(resource: &str, module: &str, timestamp: i64) -> Self {
        Self {
            operation: "observation".to_string(),
            resource: resource.to_string(),
            module: module.to_string(),
            timestamp,
            source: None,
            attribute: None,
            old_value: None,
            new_value: None,
        }
    }

    pub fn change(
        resource: &str,
        module: &str,
        attribute: &str,
        old_value: &str,
        new_value: &str,
        timestamp: i64,
    ) -> Self {
        Self {
            operation: "change".to_string(),
            resource: resource.to_string(),
            module: module.to_string(),
            timestamp,
            source: None,
            attribute: Some(attribute.to_string()),
            old_value: Some(old_value.to_string()),
            new_value: Some(new_value.to_string()),
        }
    }

    /// Return a copy with the timestamp removed, for checksum-based deduplication.
    pub fn without_timestamp(&self) -> serde_json::Value {
        let mut val = serde_json::to_value(self).unwrap();
        if let Some(obj) = val.as_object_mut() {
            obj.remove("timestamp");
        }
        val
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleResponse {
    pub operation: String,
    pub resource: String,
    pub module: String,
    pub timestamp: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub attribute: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub value: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub old_value: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub new_value: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub severity: Option<String>,
}

pub struct Discovery {
    pub resource: String,
    pub module: String,
    pub source: String,
}

pub struct Observation {
    pub resource: String,
    pub module: String,
    pub attribute: String,
    pub value: String,
    pub timestamp: chrono::NaiveDateTime,
    pub severity: String,
}

pub struct Resource {
    pub resource: String,
    pub module: String,
    pub source: Option<String>,
}

impl Resource {
    pub fn from_discovery(d: &Discovery) -> Self {
        Self {
            resource: d.resource.clone(),
            module: d.module.clone(),
            source: Some(d.source.clone()),
        }
    }
}

pub struct Change {
    pub resource: String,
    pub module: String,
    pub attribute: String,
    pub old_value: String,
    pub new_value: String,
    pub severity: String,
    pub timestamp: i64,
}

impl Change {
    pub fn to_request(&self) -> ModuleRequest {
        ModuleRequest::change(
            &self.resource,
            &self.module,
            &self.attribute,
            &self.old_value,
            &self.new_value,
            self.timestamp,
        )
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigTarget {
    pub modules: Vec<String>,
    pub resources: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleConfig {
    pub command: String,
    #[serde(default)]
    pub slow: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub targets: Vec<ConfigTarget>,
    pub modules: HashMap<String, ModuleConfig>,
}

/// Convert a serde_json::Value to a string suitable for database storage.
/// Dicts and lists are stored as JSON strings, scalars as plain strings.
pub fn value_to_db_string(v: &serde_json::Value) -> String {
    match v {
        serde_json::Value::String(s) => s.clone(),
        serde_json::Value::Number(n) => n.to_string(),
        serde_json::Value::Null => String::new(),
        _ => serde_json::to_string(v).unwrap_or_default(),
    }
}
