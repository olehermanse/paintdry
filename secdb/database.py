from os import abort
from time import sleep

import psycopg2

from secdb.lib import Observation, Resource


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

    def upsert_resource(self, resource: Resource, source):
        return self._query(
            """
            INSERT INTO resources (module, resource, source)
            VALUES(%s, %s, %s)
            ON CONFLICT ON CONSTRAINT resources_constraint
            DO UPDATE SET last_seen = NOW()
            """,
            (resource.module, resource.resource, source),
        )

    def upsert_observations(self, observation: Observation):
        module = observation.module
        attribute = observation.attribute
        resource = observation.resource
        value = observation.value
        timestamp = observation.timestamp
        return self._query(
            """
            INSERT INTO observations (module, attribute, resource, value, first_seen, last_changed, last_seen)
            VALUES(%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT observations_constraint
            DO UPDATE SET last_seen = %s,
            value = EXCLUDED.value,
            last_changed = CASE
            WHEN observations.value IS DISTINCT FROM EXCLUDED.value THEN %s
            ELSE observations.last_changed END;
            """,
            (
                module,
                attribute,
                resource,
                value,
                timestamp,
                timestamp,
                timestamp,
                timestamp,
                timestamp,
            ),
        )

    def get_resource(self, id: int) -> Resource | None:
        rows = self._query(
            """
            SELECT id, resource, module, source, first_seen, last_seen
            FROM resources
            WHERE id=%s;
            """,
            (id,),
        )
        if not rows:
            return None
        results = []
        for row in rows:
            resource = Resource(
                id=row[0],
                resource=row[1],
                module=row[2],
                source=row[3],
                first_seen=row[4],
                last_seen=row[5],
            )
            results.append(resource)
        if len(results) == 1:
            return results[0]
        return None

    def get_resources(self) -> list[Resource]:
        rows = self._query(
            """
            SELECT id, resource, module, source, first_seen, last_seen
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
                module=row[2],
                source=row[3],
                first_seen=row[4],
                last_seen=row[5],
            )
            results.append(resource)
        return results

    def _select(
        self, table: str, columns: list[str], where: dict | None = None
    ) -> list[dict]:
        where_part = ""
        where_keys = []
        where_values = []
        if where:
            for key, value in where.items():
                where_keys.append(key)
                where_values.append(value)
            strings = [f"{key}=%s" for key in where_keys]
            where_part = "WHERE " + " AND ".join(strings)

        query = f"""
        SELECT {', '.join(columns)}
        FROM {table}
        {where_part}
        ;
        """

        rows = self._query(query, where_values) if where else self._query(query)
        if not rows:
            return []
        results = []
        for row in rows:
            d = {}
            for key, value in zip(columns, row):
                d[key] = value
            results.append(d)
        return results

    def get_observations(self) -> list[Observation]:
        objects = self._select(
            "observations",
            [
                "id",
                "resource",
                "module",
                "attribute",
                "value",
                "first_seen",
                "last_changed",
                "last_seen",
            ],
        )
        if not objects:
            return []
        results = []
        for object in objects:
            result = Observation(**object)
            results.append(result)
        return results

    def get_observation(self, id: int) -> Observation | None:
        rows = self._query(
            """
            SELECT id, resource, module, attribute, value, first_seen, last_changed, last_seen
            FROM observations
            WHERE id=%s;
            """,
            (id,),
        )
        if not rows:
            return None
        results = []
        for row in rows:
            observation = Observation(
                id=row[0],
                resource=row[1],
                module=row[2],
                attribute=row[3],
                value=row[4],
                first_seen=row[5],
                last_changed=row[6],
                last_seen=row[7],
            )
            results.append(observation)
        if len(results) == 1:
            return results[0]
        return None

    def get_history(self, id:int|None=None) -> list[dict]:
        singular = (id is not None)
        objects = self._select(
            "history",
            [
                "id",
                "resource",
                "module",
                "attribute",
                "value",
                "timestamp",
            ],
            {"id": id} if singular else None,
        )
        if not objects:
            return []
        results = []
        for object in objects:
            results.append(object)
        return results

    def get_changes(self, id:int|None=None) -> list[dict]:
        singular = (id is not None)
        objects = self._select(
            "changes",
            [
                "id",
                "resource",
                "module",
                "attribute",
                "old_value",
                "new_value",
                "timestamp",
            ],
            {"id": id} if singular else None,
        )
        if not objects:
            return []
        results = []
        for object in objects:
            results.append(object)
        return results
