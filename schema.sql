CREATE TABLE IF NOT EXISTS index (
  entry_id serial PRIMARY KEY,
  entry TEXT NOT NULL UNIQUE,
  metadata TEXT DEFAULT NULL,
  urls TEXT[] DEFAULT NULL,
  first_seen TIMESTAMP DEFAULT NOW(),
  last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS history (
  entry_id serial PRIMARY KEY,
  entry TEXT NOT NULL,
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

INSERT INTO index (entry)
  VALUES('test_entry')
  ON CONFLICT (entry)
  DO UPDATE SET last_seen = NOW();
