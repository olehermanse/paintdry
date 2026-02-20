use postgres::{Client, NoTls};
use std::thread;
use std::time::Duration;

use crate::types::{Change, Observation, Resource};

fn to_json(value: &str) -> String {
    value.to_string()
}

fn connect_loop() -> Client {
    loop {
        match Client::connect(
            "host=postgres dbname=postgres user=postgres password=postgres",
            NoTls,
        ) {
            Ok(client) => {
                println!("Connected to PG");
                return client;
            }
            Err(e) => {
                println!("Database not ready, waiting... ({})", e);
                thread::sleep(Duration::from_secs(2));
            }
        }
    }
}

pub struct Database {
    client: Client,
}

impl Database {
    pub fn new() -> Self {
        Self {
            client: connect_loop(),
        }
    }

    fn query(&mut self, query: &str, params: &[&(dyn postgres::types::ToSql + Sync)]) {
        self.client.execute(query, params).unwrap_or_else(|e| {
            eprintln!("Query failed: {}", e);
            0
        });
    }

    pub fn update_change(&mut self, change: &Change) {
        self.query(
            "UPDATE changes
             SET severity=$1
             WHERE (severity='' OR severity='unknown')
               AND resource=$2 AND attribute=$3
               AND old_value=$4 AND new_value=$5",
            &[
                &change.severity,
                &change.resource,
                &change.attribute,
                &to_json(&change.old_value),
                &to_json(&change.new_value),
            ],
        );
    }

    pub fn upsert_resource(&mut self, resource: &Resource, source: &str) {
        self.query(
            "INSERT INTO resources (module, resource, source)
             VALUES($1, $2, $3)
             ON CONFLICT ON CONSTRAINT resources_constraint
             DO UPDATE SET last_seen = NOW()",
            &[&resource.module, &resource.resource, &source],
        );
    }

    pub fn upsert_observation(&mut self, obs: &Observation) {
        self.client
            .execute(
                "INSERT INTO observations (module, attribute, resource, value, first_seen, last_changed, last_seen, severity)
                 VALUES($1, $2, $3, $4, $5, $6, $7, $8)
                 ON CONFLICT ON CONSTRAINT observations_constraint
                 DO UPDATE SET last_seen = $9,
                 value = EXCLUDED.value,
                 severity = EXCLUDED.severity,
                 last_changed = CASE
                   WHEN observations.value IS DISTINCT FROM EXCLUDED.value THEN $10
                   ELSE observations.last_changed END",
                &[
                    &obs.module,
                    &obs.attribute,
                    &obs.resource,
                    &obs.value,
                    &obs.timestamp,
                    &obs.timestamp,
                    &obs.timestamp,
                    &obs.severity,
                    &obs.timestamp,
                    &obs.timestamp,
                ],
            )
            .unwrap_or_else(|e| {
                eprintln!("upsert_observation failed: {}", e);
                0
            });
    }

    pub fn get_resources(&mut self) -> Vec<Resource> {
        let rows = self
            .client
            .query(
                "SELECT resource, module, source FROM resources",
                &[],
            )
            .unwrap_or_else(|e| {
                eprintln!("get_resources failed: {}", e);
                vec![]
            });
        rows.iter()
            .map(|row| Resource {
                resource: row.get(0),
                module: row.get(1),
                source: row.get(2),
            })
            .collect()
    }

    pub fn get_new_changes(&mut self) -> Vec<Change> {
        let rows = self
            .client
            .query(
                "SELECT resource, module, attribute, old_value, new_value, timestamp
                 FROM changes
                 WHERE severity='' OR severity='unknown'",
                &[],
            )
            .unwrap_or_else(|e| {
                eprintln!("get_new_changes failed: {}", e);
                vec![]
            });
        rows.iter()
            .map(|row| {
                let ts: chrono::NaiveDateTime = row.get(5);
                Change {
                    resource: row.get(0),
                    module: row.get(1),
                    attribute: row.get(2),
                    old_value: row.get(3),
                    new_value: row.get(4),
                    severity: String::new(),
                    timestamp: ts.and_utc().timestamp(),
                }
            })
            .collect()
    }
}
