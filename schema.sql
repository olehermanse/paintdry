CREATE OR REPLACE FUNCTION json_to_string(json_column TEXT) RETURNS TEXT AS $$
DECLARE
    formatted_text TEXT;
BEGIN
    -- Try to convert and check JSON type
    IF json_column='[]' THEN
        formatted_text := '(Empty list)';
    ELSIF json_column='""' THEN
        formatted_text := '(Empty string)';
    ELSIF json_column='' THEN
        formatted_text := '(Empty string)';
    ELSIF json_column='{}' THEN
        formatted_text := '(Empty object)';
    ELSIF jsonb_typeof(json_column::JSONB) = 'array' THEN
        SELECT string_agg(element, ', ')
        INTO formatted_text
        FROM jsonb_array_elements_text(json_column::JSONB) AS element;
    ELSE
        -- Not an array, just return the text form of the JSON
        formatted_text := json_column::TEXT;
    END IF;
    RETURN formatted_text;
EXCEPTION
    WHEN invalid_text_representation THEN
        -- Not valid JSON - just return the raw text
        RETURN json_column::TEXT;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE TABLE IF NOT EXISTS resources (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    source TEXT NOT NULL,
    first_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT resources_constraint UNIQUE (resource, module, source)
);

CREATE TABLE IF NOT EXISTS observations (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    first_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_changed TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    severity TEXT NOT NULL DEFAULT '',
    CONSTRAINT observations_constraint UNIQUE (module, attribute, resource)
);

ALTER TABLE observations ADD COLUMN IF NOT EXISTS severity TEXT NOT NULL DEFAULT '';

CREATE OR REPLACE VIEW pretty_observations AS
SELECT module, resource, attribute, json_to_string(value) AS value, first_seen, last_changed, last_seen
FROM observations;

CREATE TABLE IF NOT EXISTS history (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT history_constraint UNIQUE (module, attribute, resource, timestamp)
);

CREATE TABLE IF NOT EXISTS changes (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    old_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    severity TEXT NOT NULL DEFAULT '',
    CONSTRAINT changes_constraint UNIQUE (module, attribute, resource, timestamp, old_value, new_value)
);

ALTER TABLE changes ADD COLUMN IF NOT EXISTS severity TEXT NOT NULL DEFAULT '';

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
