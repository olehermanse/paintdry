CREATE TABLE IF NOT EXISTS config (
    serial_id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_changed TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    CONSTRAINT config_constraint UNIQUE (module, resource)
);

CREATE TABLE IF NOT EXISTS resources (
    serial_id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    modules TEXT[] NOT NULL,
    source TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    CONSTRAINT resources_constraint UNIQUE (resource)
);

CREATE TABLE IF NOT EXISTS observations (
    serial_id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_changed TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    CONSTRAINT observations_constraint UNIQUE (module, attribute, resource)
);

CREATE TABLE IF NOT EXISTS history (
    serial_id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    ts TIMESTAMP DEFAULT NOW(),
    CONSTRAINT history_constraint UNIQUE (module, attribute, resource, ts)
);

CREATE TABLE IF NOT EXISTS events (
    serial_id serial PRIMARY KEY,
    ts TIMESTAMP,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    old_value TEXT NOT NULL,
    CONSTRAINT events_constraint UNIQUE (module, attribute, resource, ts)
);
