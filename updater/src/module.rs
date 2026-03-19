use std::fs;
use std::io::Read;
use std::path::Path;
use std::process::{Child, Command, Stdio};

use crate::types::ModuleRequest;
use crate::utils::{dump_json_atomic, sha256};

pub struct Module {
    pub name: String,
    pub slow: bool,
    command: String,
    input_folder: String,
    output_folder: String,
    process: Option<Child>,
    request_backlog: Vec<ModuleRequest>,
}

impl Module {
    pub fn new(name: &str, command: &str, slow: bool) -> Self {
        println!("Starting '{}' module", name);

        assert!(!name.contains(' '));
        assert!(!name.contains('/'));
        assert!(!name.contains(','));
        assert!(!name.contains('.'));
        assert!(!name.contains('\''));
        assert!(!name.contains('"'));
        assert!(!name.contains('\n'));

        let module_folder = format!("/paintdry/mount-state/modules/{}", name);
        let cache_folder = "/paintdry/mount-state/".to_string();
        let input_folder = format!("{}/requests", module_folder);
        let output_folder = format!("{}/responses", module_folder);

        fs::create_dir_all(&input_folder).ok();
        fs::create_dir_all(&output_folder).ok();
        fs::create_dir_all(&cache_folder).ok();

        let full_command = format!(
            "{} '{}' '{}' '{}' 2>&1",
            command, input_folder, output_folder, cache_folder
        );

        Self {
            name: name.to_string(),
            slow,
            command: full_command,
            input_folder,
            output_folder,
            process: None,
            request_backlog: Vec::new(),
        }
    }

    pub fn output_folder(&self) -> &str {
        &self.output_folder
    }

    pub fn wait(&mut self) {
        self.wait_process();
    }

    fn wait_process(&mut self) {
        if self.slow {
            return;
        }
        if let Some(mut child) = self.process.take() {
            let mut stdout_buf = String::new();
            if let Some(ref mut stdout) = child.stdout {
                stdout.read_to_string(&mut stdout_buf).ok();
            }
            let stdout_buf = stdout_buf.trim();
            if !stdout_buf.is_empty() {
                println!("Stdout from {} module:", self.name);
                println!("{}", stdout_buf);
            }

            match child.wait() {
                Ok(status) => {
                    if !status.success() {
                        println!(
                            "Module {} exited with error: {}",
                            self.name,
                            status.code().unwrap_or(-1)
                        );
                    }
                }
                Err(e) => {
                    println!("Failed to wait for module {}: {}", self.name, e);
                }
            }
        }
    }

    fn start_process(&mut self) {
        if self.slow {
            return;
        }
        self.wait_process();
        match Command::new("bash")
            .arg("-c")
            .arg(&self.command)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
        {
            Ok(child) => {
                self.process = Some(child);
            }
            Err(e) => {
                eprintln!("Failed to start module {}: {}", self.name, e);
            }
        }
    }

    fn dump_backlog(&mut self) {
        let backlog: Vec<ModuleRequest> = self.request_backlog.drain(..).collect();
        self.write_requests(&backlog);
    }

    pub fn start(&mut self) {
        if self.process.is_some() {
            return;
        }
        self.dump_backlog();
        self.start_process();
    }

    fn write_requests_with_checksum(&mut self, requests: &[ModuleRequest]) {
        let data: Vec<serde_json::Value> =
            requests.iter().map(|r| r.without_timestamp()).collect();
        let json_str = serde_json::to_string(&data).unwrap();
        let checksum = sha256(&json_str);
        let path = format!("{}/{}.json", self.input_folder, checksum);
        if Path::new(&path).exists() {
            return;
        }
        let value = serde_json::to_value(requests).unwrap();
        dump_json_atomic(&path, &value);
    }

    pub fn write_requests(&mut self, requests: &[ModuleRequest]) {
        if requests.is_empty() {
            return;
        }
        self.write_requests_with_checksum(requests);
    }

    pub fn send_requests(&mut self, requests: Vec<ModuleRequest>) {
        self.request_backlog.extend(requests);
        self.start();
    }
}

impl Drop for Module {
    fn drop(&mut self) {
        if let Some(mut child) = self.process.take() {
            child.kill().ok();
            child.wait().ok();
        }
    }
}
