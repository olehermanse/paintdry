import json
from time import sleep

import psycopg2

from secdb.modules.lib import ConfigTarget, Observation, Resource


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

    def upsert_config(self, target: ConfigTarget):
        return self._query(
            """
            INSERT INTO config (module, resource)
            VALUES(%s, %s)
            ON CONFLICT ON CONSTRAINT config_constraint
            DO UPDATE SET last_seen = NOW()
            """,
            (target.module, target.resource),
        )

    def upsert_resource(self, resource: Resource, source):
        return self._query(
            """
            INSERT INTO resources (modules, resource, source)
            VALUES(%s, %s, %s)
            ON CONFLICT ON CONSTRAINT resources_constraint
            DO UPDATE SET last_seen = NOW()
            """,
            (resource.modules, resource.resource, source),
        )

    def upsert_observations(self, observation: Observation):
        module = observation.module
        attribute = observation.attribute
        resource = observation.resource
        value = observation.value
        timestamp = observation.timestamp
        return self._query(
            """
            INSERT INTO observations (module, attribute, resource, value)
            VALUES(%s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT observations_constraint
            DO UPDATE SET last_seen = %s, value = %s
            """,
            (module, attribute, resource, value, timestamp, value),
        )

    def get_resources(self) -> list[Resource]:
        rows = self._query(
            """
            SELECT id, resource, modules, source, first_seen, last_seen
            FROM resources;
            """
        )
        if not rows:
            return []
        results = []
        for row in rows:
            resource = Resource(
                id=row[0],
                resource=row[1],
                modules=row[2],
                source=row[3],
                first_seen=row[4],
                last_seen=row[5],
            )
            results.append(resource)
        return results

    def _select_dicts(self, table: str, keys: list[str]) -> list[dict]:
        query = f"""
        SELECT {', '.join(keys)}
        FROM {table};
        """
        rows = self._query(query)
        if not rows:
            return []
        results = []
        for row in rows:
            d = {}
            for key, value in zip(keys, row):
                d[key] = value
            results.append(d)
        return results

    def get_observations(self) -> list[Observation]:
        objects = self._select_dicts("observations", ["id", "resource", "module", "attribute", "value", "first_seen", "last_changed", "last_seen"])
        if not objects:
            return []
        results = []
        for object in objects:
            result = Observation(**object)
            results.append(result)
        return results

    def get_observation(self, resource):
        rows = self._query(
            """
            SELECT module, attribute, resource, value, first_seen, last_seen
            FROM observations
            WHERE resource=%s;
            """,
            (resource,),
        )
        if not rows:
            return []
        results = []
        for row in rows:
            results.append(
                {
                    "module": row[0],
                    "attribute": row[1],
                    "resource": row[2],
                    "value": row[3],
                    "first_seen": row[4].timestamp(),
                    "last_seen": row[5].timestamp(),
                }
            )
        return results

    def get_one_of(self, possibilities):
        for x in possibilities:
            r = self.get_observation(x)
            if r:
                return r
        return None

    def get_observations_resources(self):
        return self._query("SELECT DISTINCT resource FROM observations;")
