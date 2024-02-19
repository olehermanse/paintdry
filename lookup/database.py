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

    def upsert_config(self, entry):
        module, identifier = (
            entry["module"],
            entry["identifier"],
        )
        return self._query(
            """
            INSERT INTO config (module, identifier)
            VALUES(%s, %s)
            ON CONFLICT ON CONSTRAINT config_constraint
            DO UPDATE SET last_seen = NOW()
            """,
            (module, identifier),
        )

    def upsert_resources(self, entry):
        module, type, identifier, value = (
            entry["module"],
            entry["type"],
            entry["identifier"],
            entry["value"],
        )
        return self._query(
            """
            INSERT INTO resources (module, type, identifier, value)
            VALUES(%s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT resources_constraint
            DO UPDATE SET last_seen = NOW(), value = %s
            """,
            (module, type, identifier, value, value),
        )

    def get_resource(self, identifier):
        rows = self._query(
            """
            SELECT module, type, identifier, value, first_seen, last_seen
            FROM resources
            WHERE identifier=%s;
            """,
            (identifier,),
        )
        if not rows:
            return None
        module, type, identifier, value, first_seen, last_seen = rows[0]
        return {
            "module": module,
            "type": type,
            "identifier": identifier,
            "value": value,
            "first_seen": first_seen,
            "last_seen": last_seen,
        }

    def get_one_of(self, possibilities):
        for x in possibilities:
            r = self.get_resource(x)
            if r:
                return r
        return None

    def get_resources_identifiers(self):
        return self._query("SELECT DISTINCT identifier FROM resources;")
