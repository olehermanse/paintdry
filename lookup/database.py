import json
from time import sleep

import psycopg2


def connect_loop():
    while True:
        try:
            conn = psycopg2.connect(
                "host='postgres' dbname='postgres' user='postgres' host='postgres' password='postgres'"
            )
            print("Connected to PG")
            return conn
        except:
            print("Database not ready, waiting...")
            sleep(2)


class Database:
    def __init__(self):
        self.connection = connect_loop()

    def _query(self, query, args=None):
        conn = self.connection
        cur = conn.cursor()
        if args:
            cur.execute(query, args)
        else:
            cur.execute(query)
        result = []
        while True:
            try:
                row = cur.fetchone()
            except:
                break
            if not row:
                break
            result.append(row)
        conn.commit()
        cur.close()
        return result

    def upsert_entry(self, key, metadata=None, urls=None):
        return self._query(
            """
          INSERT INTO index (identifier)
            VALUES(%s)
            ON CONFLICT (identifier)
            DO UPDATE SET last_seen = NOW();
        """,
            (key,),
        )

    def upsert_link(self, a, text, b):
        pass

    def create_related_hash(self, key, value):
        hash = sha(key)
        entry = {
            "id": hash,
            "string": key,
            "type": "string_hash",
            "links": {key: "string_hash_source"},
        }
        self._upsert(entry)
        return hash

    def insert_entry(self, key, value):
        value = copy.deepcopy(value)
        value["id"] = key
        hash = self.create_related_hash(key, value)
        value["links"] = {hash: "string_hash"}
        return self._upsert(value)

    def get_entry(self, key):
        rows = self._query(
            """
            SELECT identifier, metadata, urls, first_seen, last_seen FROM index WHERE identifier=%s;
        """,
            (key,),
        )
        if not rows:
            return None
        r = rows[0]
        identifier = r[0]
        metadata = json.loads(r[1]) if r[1] else None
        urls = json.loads(r[2]) if r[2] else None
        first_seen = r[3]
        last_seen = r[4]
        return {
            "identifier": identifier,
            "metadata": metadata,
            "urls": urls,
            "first_seen": first_seen,
            "last_seen": last_seen,
        }

    def get_one_of(self, possibilities):
        for x in possibilities:
            r = self.get_entry(x)
            if r:
                return r
        return None

    def get_keys(self):
        return self._query(
            """
            SELECT identifier FROM index;
        """
        )
