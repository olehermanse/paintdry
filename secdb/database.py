from os import abort
from time import sleep

import psycopg2

from secdb.lib import Observation, Resource, Change


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

    def update_change(self, change: Change):
        return self._query(
            """
            UPDATE changes
            SET severity=%s
            WHERE (severity='' OR severity='unknown') AND resource=%s AND attribute=%s AND old_value=%s AND new_value=%s
            """,
            (
                change.severity,
                change.resource,
                change.attribute,
                change.old_value,
                change.new_value,
            ),
        )

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
        severity = observation.severity
        return self._query(
            """
            INSERT INTO observations (module, attribute, resource, value, first_seen, last_changed, last_seen, severity)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT observations_constraint
            DO UPDATE SET last_seen = %s,
            value = EXCLUDED.value,
            severity = EXCLUDED.severity,
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
                severity,
                timestamp,
                timestamp,
            ),
        )

    def get_resource(self, id: str) -> Resource | None:
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
        where_statements = []
        where_values = []
        if where:
            for key, value in where.items():
                if type(value) is list and len(value) == 1:
                    where_values.append(value[0])
                    where_statements.append(f"{key}=%s")
                elif type(value) is not list:
                    where_values.append(value)
                    where_statements.append(f"{key}=%s")
                else:
                    assert type(value) is list and len(value) > 1
                    where_values.extend(value)
                    or_statements = [f"{key}=%s"] * len(value)
                    where_statements.append(f"( {' OR '.join(or_statements)} )")
            where_part = "WHERE " + " AND ".join(where_statements)

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
                "severity",
            ],
        )
        if not objects:
            return []
        results = []
        for object in objects:
            result = Observation(**object)
            results.append(result)
        return results

    def get_observation(self, id: str) -> Observation | None:
        rows = self._query(
            """
            SELECT id, resource, module, attribute, value, first_seen, last_changed, last_seen, severity
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
                severity=row[8],
            )
            results.append(observation)
        if len(results) == 1:
            return results[0]
        return None

    def get_history(self, id: str | None = None) -> list[dict]:
        singular = id is not None
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

    def get_changes(self, id: str | None = None) -> list[dict]:
        singular = id is not None
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

    def get_new_changes(self) -> list[Change]:
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
            {"severity": ["", "unknown"]},
        )
        if not objects:
            return []
        results = []
        for object in objects:
            results.append(Change(**object))
        return results

    def search(self, search_string: str) -> dict:
        """Search across resources, observations, and changes tables."""
        if not search_string:
            return {"query": search_string, "results": []}

        search_pattern = f"%{search_string}%"
        results = []

        # Search resources
        resource_rows = self._query(
            """
            SELECT id, resource, module, source, first_seen, last_seen
            FROM resources
            WHERE resource LIKE %s
               OR module LIKE %s
               OR source LIKE %s
            LIMIT 50;
            """,
            (search_pattern, search_pattern, search_pattern)
        )

        for row in resource_rows:
            results.append({
                "type": "resource",
                "id": str(row[0]),
                "resource": row[1],
                "module": row[2],
                "source": row[3],
                "first_seen": row[4].isoformat() if row[4] else None,
                "last_seen": row[5].isoformat() if row[5] else None,
            })

        # Search observations
        observation_rows = self._query(
            """
            SELECT id, resource, module, attribute, value, first_seen, last_seen, severity
            FROM observations
            WHERE resource LIKE %s
               OR module LIKE %s
               OR attribute LIKE %s
               OR value LIKE %s
            LIMIT 50;
            """,
            (search_pattern, search_pattern, search_pattern, search_pattern)
        )

        for row in observation_rows:
            result = {
                "type": "observation",
                "id": str(row[0]),
                "resource": row[1],
                "module": row[2],
                "attribute": row[3],
                "value": row[4],
                "first_seen": row[5].isoformat() if row[5] else None,
                "last_seen": row[6].isoformat() if row[6] else None,
            }
            if row[7]:  # severity
                result["severity"] = row[7]
            results.append(result)

        # Search changes
        change_rows = self._query(
            """
            SELECT id, resource, module, attribute, old_value, new_value, timestamp, severity
            FROM changes
            WHERE resource LIKE %s
               OR module LIKE %s
               OR attribute LIKE %s
               OR old_value LIKE %s
               OR new_value LIKE %s
            LIMIT 50;
            """,
            (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)
        )

        for row in change_rows:
            result = {
                "type": "change",
                "id": str(row[0]),
                "resource": row[1],
                "module": row[2],
                "attribute": row[3],
                "old_value": row[4],
                "new_value": row[5],
                "timestamp": row[6].isoformat() if row[6] else None,
            }
            if row[7]:
                result["severity"] = row[7]
            results.append(result)

        return {
            "query": search_string,
            "results": results
        }
