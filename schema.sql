CREATE OR REPLACE FUNCTION json_to_string(json_column TEXT) RETURNS TEXT AS $$
DECLARE
    formatted_text TEXT;
BEGIN
    -- Try to recognize the data based on hardcoded edge cases, or JSON type:
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
        -- Not recognized / handled, just default to original
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

DROP VIEW IF EXISTS observations_pretty;
CREATE VIEW observations_pretty AS
SELECT module, resource, attribute, json_to_string(value) AS value, severity, first_seen, last_changed, last_seen
FROM observations;

DROP VIEW IF EXISTS observations_severity;
CREATE VIEW observations_severity AS
SELECT * FROM observations
WHERE severity != '' AND severity != 'none'
ORDER BY
    CASE severity WHEN 'none' THEN 0
                  WHEN 'recommendation' THEN 1
                  WHEN 'low' THEN 2
                  WHEN 'medium' THEN 3
                  WHEN 'high' THEN 4
                  WHEN 'critical' THEN 5
    ELSE 10 END DESC;

CREATE TABLE IF NOT EXISTS history (
    id serial PRIMARY KEY,
    resource TEXT NOT NULL,
    module TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT history_constraint UNIQUE (module, attribute, resource, timestamp)
);

DROP VIEW IF EXISTS history_pretty;
CREATE VIEW history_pretty AS
SELECT module, resource, attribute, json_to_string(value) AS value, timestamp
FROM history;

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

DROP VIEW IF EXISTS changes_pretty;
CREATE VIEW changes_pretty AS
SELECT module, resource, attribute, json_to_string(old_value) AS old_value, json_to_string(new_value) AS new_value, severity, timestamp
FROM changes;

DROP VIEW IF EXISTS changes_severity;
CREATE VIEW changes_severity AS
SELECT * FROM
(
  SELECT DISTINCT ON (module, resource, attribute)
    id, module, resource, attribute, old_value, new_value, timestamp, severity
  FROM changes
  ORDER BY module, resource, attribute, timestamp DESC
)
WHERE severity != 'none'
ORDER BY
CASE severity
    WHEN 'critical' THEN 5
    WHEN 'high' THEN 4
    WHEN 'medium' THEN 3
    WHEN 'low' THEN 2
    WHEN 'recommendation' THEN 1
    WHEN 'notice' THEN 0
ELSE 10 END DESC, timestamp DESC;

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
