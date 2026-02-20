# Updater

Rust implementation of the paintdry updater, replacing the previous `scripts/updater.sh` + Python `paintdry/update.py` combo.

## What it does

The updater is responsible for:

- Cleaning up old module request/response JSON files
- Applying the database schema (with retry until postgres is ready)
- Running the main update loop every 60 seconds:
  1. Read config (`config.json` or `config-override.json`)
  2. Start modules (subprocess-based Python scripts)
  3. Send change requests for unassessed changes in the DB
  4. Send discovery/observation requests for config targets
  5. Send discovery/observation requests for all DB resources
  6. Wait for module responses and process them (upsert to DB)
  7. Send change requests again for any newly detected changes
  8. Save snapshot metadata

## Source files

| File              | Purpose                                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| `src/main.rs`     | Entry point: cleanup, schema application, main loop                                                       |
| `src/updater.rs`  | `Updater` struct orchestrating the full update cycle                                                      |
| `src/module.rs`   | Module subprocess management: request files, process lifecycle, response files                            |
| `src/database.rs` | PostgreSQL client: upsert resources/observations, update changes, queries                                 |
| `src/types.rs`    | Data types: `ModuleRequest`, `ModuleResponse`, `Discovery`, `Observation`, `Resource`, `Change`, `Config` |
| `src/config.rs`   | Config file loading                                                                                       |
| `src/utils.rs`    | SHA256 hashing, timestamps, folder creation, atomic JSON writes                                           |

## Dependencies

- `serde` / `serde_json` - JSON serialization
- `postgres` (with `with-chrono-0_4` feature) - PostgreSQL client
- `sha2` - SHA256 checksums for request deduplication
- `chrono` - timestamps

## Module interaction

Modules are Python scripts that communicate via JSON files on disk:

- Requests written to `/paintdry/mount-state/modules/{name}/requests/*.json`
- Responses read from `/paintdry/mount-state/modules/{name}/responses/*.json`
- Request files are deduplicated by SHA256 of content (excluding timestamp)
- Response files are deleted after processing

Modules are started as subprocesses with: `cd '{module_folder}' && {command} '{input_folder}' '{output_folder}' '{cache_folder}'`

"Slow" modules (e.g. github) are not started/waited by the updater - they run externally via the downloader.

## Building

```
cargo build          # debug build
cargo build --release # release build
cargo check          # type-check only
```

## What is NOT in this crate

- Python modules (`modules/`) - still Python, invoked as subprocesses
- Server / API (`paintdry/server.py`) - stays Python
- Downloader (`scripts/downloader.sh`) - stays as shell + Python
- GUI (`gui/`) - React frontend, untouched
