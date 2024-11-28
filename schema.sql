CREATE TABLE IF NOT EXISTS resources (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    modules TEXT[] NOT NULL,
    source TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    CONSTRAINT resources_constraint UNIQUE (resource)
);

CREATE TABLE IF NOT EXISTS observations (
    id serial PRIMARY KEY,
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
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    CONSTRAINT history_constraint UNIQUE (module, attribute, resource, timestamp)
);

CREATE TABLE IF NOT EXISTS changes (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    old_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    CONSTRAINT changes_constraint UNIQUE (module, attribute, resource, timestamp, old_value, new_value)
);

CREATE OR REPLACE FUNCTION observations_to_history_function()
RETURNS TRIGGER AS $observations_to_history_function$
BEGIN
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE' AND NEW.value != OLD.value) THEN
        INSERT INTO history(resource, module, attribute, value, timestamp)
        VALUES (NEW.resource, NEW.module, NEW.attribute, NEW.value, NEW.last_changed)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NULL;
END;
$observations_to_history_function$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER observations_to_history_trigger
    AFTER INSERT OR UPDATE ON observations
    FOR EACH ROW EXECUTE FUNCTION observations_to_history_function();

CREATE OR REPLACE FUNCTION observations_to_changes_function()
RETURNS TRIGGER AS $observations_to_changes_function$
BEGIN
    IF (NEW.value != OLD.value) THEN
        INSERT INTO changes(resource, module, attribute, old_value, new_value, timestamp)
        VALUES (NEW.resource, NEW.module, NEW.attribute, OLD.value, NEW.value, NEW.last_changed)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NULL;
END;
$observations_to_changes_function$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER observations_to_changes_trigger
    AFTER INSERT OR UPDATE ON observations
    FOR EACH ROW EXECUTE FUNCTION observations_to_changes_function();
