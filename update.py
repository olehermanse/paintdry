import os
import sys
import copy

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

class LookUpDB:
    def __init__(self):
        self.database = None

    def _upsert(self, entry):
        assert "id" in entry
        index_id = entry["id"]
        target = {}
        if index_id in self.database["index"]:
            target = self.database["index"][index_id]
        new_entry = merge(target, entry)
        self.database["index"][index_id] = new_entry
        self.database.save()
        return self.database["index"][index_id]

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
        assert entry["id"] in self.database["index"]
        self.database["index"][entry["id"]] = entry
        self.database.save()
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

    def process_website_single(self, entry):
        print(f'Website: {entry["url"]}')
        entry = self.insert_entry(entry["url"], entry)
        target_folder = os.path.join(self.snapshot, get_link(entry, "string_hash"))
        ensure_folder(target_folder)
        destination = os.path.join(target_folder, "index.html")
        r, out, err = shell(f'curl {entry["url"]} -o {destination}')
        r, out, err = shell(f'cd {target_folder} && prettier --no-color index.html')
        if err:
            self.add_alert(entry, error=err)
        elif r != 0:
            sys.exit("Unknown error")

    def process_git_repo(self, entry):
        print(f'Git repo: {entry["url"]}')
        self.insert_entry(entry["url"], entry)

    def process(self, entry):
        match entry["type"]:
            case 'website_single':
                self.process_website_single(entry)
            case 'git_repo':
                self.process_git_repo(entry)
            case other:
                sys.exit(f"Target '{entry['type']}' in config not supported!")

    def update(self):
        # Read config
        config = JsonFile("config.json")

        # Setup state
        state = ensure_folder("./state")
        self.database = JsonFile(os.path.join("state", "database.json"))
        if not "index" in self.database:
            self.database["index"] = {}
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
        self.database.save()
        self.database.save(os.path.join(self.snapshot, "database.json"))

def main():
    db = LookUpDB()
    db.update()

if __name__ == "__main__":
    main()
