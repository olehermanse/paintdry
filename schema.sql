CREATE TABLE IF NOT EXISTS index (
  serial_id serial PRIMARY KEY,
  identifier TEXT NOT NULL UNIQUE,
  metadata TEXT DEFAULT NULL,
  urls TEXT[] DEFAULT NULL,
  first_seen TIMESTAMP DEFAULT NOW(),
  last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS history (
  serial_id serial PRIMARY KEY,
  identifier TEXT NOT NULL,
  metadata TEXT DEFAULT NULL,
  urls TEXT[] DEFAULT NULL,
  first_seen TIMESTAMP DEFAULT NOW(),
  last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS links (
  src TEXT NOT NULL,
  text TEXT NOT NULL,
  dst TEXT NOT NULL
);

INSERT INTO index (identifier)
  VALUES('test_entry')
  ON CONFLICT (identifier)
  DO UPDATE SET last_seen = NOW();
