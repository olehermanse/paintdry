import os
import sys
import copy
from time import sleep

import psycopg2

from utils import JsonFile, ensure_folder, ensure_json_file, shell, sha, timestamp

def get_link(entry, link_name):
    for key, value in entry["links"].items():
        if value == link_name:
            return key
    raise KeyError

def merge(a,b):
    match a:
        case str():
            return b
        case int():
            return b
        case list():
            if type(b) is list:
                return a + [x for x in b if x not in a]
            else:
                return b
        case dict():
            if type(b) is dict:
                r = copy.deepcopy(a)
                for key in b:
                    if key not in a:
                        r[key] = b[key]
                    else:
                        r[key] = merge(r[key], b[key])
                return r
            else:
                return b
    assert False

def module_website_single(updater, entry):
    print(f'Website: {entry["url"]}')
    entry = updater.insert_entry(entry["url"], entry)
    target_folder = os.path.join(updater.snapshot, get_link(entry, "string_hash"))
    ensure_folder(target_folder)
    destination = os.path.join(target_folder, "index.html")
    r, out, err = shell(f'curl {entry["url"]} -o {destination}')
    r, out, err = shell(f'cd {target_folder} && prettier --no-color index.html')
    if err:
        updater.database.add_alert(entry, error=err)
    elif r != 0:
        sys.exit("Unknown error")

def module_git_repo(updater, entry):
    print(f'Git repo: {entry["url"]}')
    updater.insert_entry(entry["url"], entry)

def connect_loop():
    while True:
        try:
            conn = psycopg2.connect("host='postgres' dbname='postgres' user='postgres' host='postgres' password='postgres'")
            print("Connected to PG")
            return conn
        except:
            print("Database not ready, waiting...")
            sleep(2)

class Database:
    def __init__(self):
        self.database_json = None
        self.connection = connect_loop()

    def _query(self, query, args=None):
        conn = self.connection
        cur = conn.cursor()
        if args:
            cur.execute(query, args)
        else:
            cur.execute(query)
        conn.commit()
        result = cur.fetchall()
        cur.close()
        return result

    def upsert_entry(self, entry, metadata):
        self.query()
        pass

    def upsert_link(self, a, text, b):
        pass

    def _upsert(self, entry):
        assert "id" in entry
        index_id = entry["id"]
        target = {}
        if index_id in self.database_json["index"]:
            target = self.database_json["index"][index_id]
        new_entry = merge(target, entry)
        self.database_json["index"][index_id] = new_entry
        self.database_json.save()
        return self.database_json["index"][index_id]

    def create_related_hash(self, key, value):
        hash = sha(key)
        entry = {
            "id": hash,
            "string": key,
            "type": "string_hash",
            "links": {key: "string_hash_source"}
        }
        self._upsert(entry)
        return hash

    def insert_entry(self, key, value):
        value = copy.deepcopy(value)
        value["id"] = key
        hash = self.create_related_hash(key, value)
        value["links"] = {hash: "string_hash"}
        return self._upsert(value)

    def update_entry(self, entry):
        assert "id" in entry
        assert entry["id"] in self.database_json["index"]
        self.database_json["index"][entry["id"]] = entry
        self.database_json.save()
        self._upsert(entry)

    def add_alert(self, entry, error):
        if not "alerts" in entry:
            entry["alerts"] = {}
        error_hash = sha(error)
        time = timestamp()

        if not error_hash in entry["alerts"]:
            entry["alerts"][error_hash] = {
                "error": error,
                "first_seen": time,
                "last_seen": time,
            }
            print(f"New alert for '{entry['id']}'")
        else:
            entry["alerts"][error_hash]["last_seen"] = time
        self.update_entry(entry)


class Updater:
    def __init__(self):
        self.database = Database()

    def insert_entry(self, key, value):
        return self.database.insert_entry(key, value)

    def process(self, entry):
        match entry["type"]:
            case "website_single":
                module_website_single(self, entry)
            case "git_repo":
                module_git_repo(self, entry)
            case other:
                sys.exit(f"Target '{entry['type']}' in config not supported!")

    def update(self):
        # Read config
        config = JsonFile("config.json")

        # Setup state
        state = ensure_folder("./state")
        self.database.database_json = JsonFile(os.path.join("state", "database.json"))
        if not "index" in self.database.database_json:
            self.database.database_json["index"] = {}
        metadata = JsonFile(os.path.join("state", "metadata.json"))

        # Setup snapshots
        snapshots = ensure_folder(os.path.join(state, "snapshots"))

        # Prepare next snapshot
        time = timestamp()
        try:
            seq = metadata["last_update"]["seq"] + 1
        except KeyError:
            seq = 1
        snapshot_name = f"{str(seq).zfill(5)}-{time}"
        self.snapshot = ensure_folder(os.path.join(snapshots, snapshot_name))

        # Actual processing
        for target in config["targets"]:
            target = copy.deepcopy(target)
            self.process(target)

        # Commit snapshot
        metadata["last_update"] = {
            "time": time,
            "name": snapshot_name,
            "seq": seq
        }
        metadata.save()
        metadata.save(os.path.join(self.snapshot, "metadata.json"))

        # TODO: No need to save database every time
        #       This is mainly here for debugging / development
        self.database.database_json.save()
        self.database.database_json.save(os.path.join(self.snapshot, "database.json"))

def main():
    if len(sys.argv) > 1:
        assert(sys.argv[1] == "forever")
        while True:
            updater = Updater()
            updater.update()
            sleep(10)
    else:
        updater = Updater()
        updater.update()

if __name__ == "__main__":
    main()
