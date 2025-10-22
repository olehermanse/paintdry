from time import sleep

import psycopg2

from paintdry.lib import Observation, Resource, Change


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

    def search(self, search_string: str, page: int = 1) -> dict:
        """Search across resources, observations, and changes tables with pagination."""
        if not search_string:
            return {
                "query": search_string,
                "results": [],
                "page": page,
                "per_page": 50,
                "total_results": 0,
                "total_pages": 0,
            }

        search_pattern = f"%{search_string}%"
        if page < 1:
            page = 1
        per_page = 50
        offset = (page - 1) * per_page

        # Search resources
        raw_results = self._query(
            """
            WITH all_results AS (
                SELECT 'resource' AS type, id, resource, module, NULL AS attribute,
                    json_build_object(
                        'first_seen', first_seen,
                        'last_seen', last_seen,
                        'source', source)
                    AS expanded_data
                FROM resources
                UNION ALL
                SELECT 'observation' AS type, id, resource, module, attribute,
                    json_build_object(
                        'first_seen', first_seen,
                        'last_seen', last_seen,
                        'value', value,
                        'severity', severity)
                    AS expanded_data
                FROM observations
                UNION ALL
                SELECT 'change' AS type, id, resource, module, attribute,
                    json_build_object(
                        'timestamp', timestamp,
                        'old_value', old_value,
                        'new_value', new_value,
                        'severity', severity)
                    AS expanded_data
                FROM changes
            ),
            filtered_results AS (
                SELECT *, COUNT(*) OVER() AS total_count
                FROM all_results
                WHERE resource LIKE %s
                      OR attribute LIKE %s
                      OR id::VARCHAR LIKE %s
                      OR type LIKE %s
                      OR expanded_data::VARCHAR LIKE %s
            )
            SELECT total_count, id, resource, attribute, type, module, expanded_data
            FROM filtered_results
            ORDER BY resource, attribute, type, module, id
            LIMIT %s OFFSET %s;
            """,
            5 * (search_pattern, ) + (per_page, offset),
        )

        results = []
        total_results = 0
        for row in raw_results:
            total_results = row[0]
            result = {
                "id": row[1],
                "resource": row[2],
                "attribute": row[3],
                "type": row[4],
                "module": row[5],
            }
            # Extract the rest optional fields inside expanded_data:
            # (timestamp, last_seen, first_seen, value, severity)
            for key, value in row[6].items():
                result[key] = value
            results.append(result)

        total_pages = 1 + total_results // per_page

        return {
            "query": search_string,
            "results": results,
            "page": page,
            "per_page": per_page,
            "total_results": total_results,
            "total_pages": total_pages,
        }
