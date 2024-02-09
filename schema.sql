CREATE TABLE IF NOT EXISTS config (
    serial_id serial PRIMARY KEY,
    module TEXT NOT NULL,
    identifier TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    CONSTRAINT config_constraint UNIQUE (module, identifier)
);

CREATE TABLE IF NOT EXISTS resources (
    serial_id serial PRIMARY KEY,
    module TEXT NOT NULL,
    type TEXT NOT NULL,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    CONSTRAINT resources_constraint UNIQUE (module, type, identifier)
);

CREATE TABLE IF NOT EXISTS history (
    serial_id serial PRIMARY KEY,
    module TEXT NOT NULL,
    type TEXT NOT NULL,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    ts TIMESTAMP DEFAULT NOW(),
    CONSTRAINT history_constraint UNIQUE (module, type, identifier, ts)
);

CREATE TABLE IF NOT EXISTS events (
    serial_id serial PRIMARY KEY,
    module TEXT NOT NULL,
    type TEXT NOT NULL,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    ts TIMESTAMP,
    old_value TEXT NOT NULL,
    old_ts TIMESTAMP,
    CONSTRAINT events_constraint UNIQUE (module, type, identifier, ts)
);
