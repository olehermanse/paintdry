import os
import sys
import copy
from time import sleep

import psycopg2
import requests

from utils import JsonFile, ensure_folder, ensure_json_file, shell, sha, timestamp
from database import Database


def get_link(entry, link_name):
    for key, value in entry["links"].items():
        if value == link_name:
            return key
    raise KeyError


def http_status_code(url):
    r = requests.get(url, allow_redirects=False)
    return r.status_code


def module_http(database, snapshot, entry):
    url = entry["identifier"]
    code = http_status_code(url)

    print(f"Website: {url} -> {code}")

    entry["type"] = "status"
    entry["value"] = code
    database.upsert_resources(entry)


class Updater:
    def __init__(self):
        self.database = Database()

    def process(self, entry):
        self.database.upsert_config(entry)
        match entry["module"]:
            case "http":
                module_http(self.database, self.snapshot, entry)
            case other:
                sys.exit(f"Target '{entry['type']}' in config not supported!")

    def update(self):
        # Read config
        config = JsonFile("config.json")

        # Setup state
        state = ensure_folder("./state")
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
        metadata["last_update"] = {"time": time, "name": snapshot_name, "seq": seq}
        metadata.save()
        metadata.save(os.path.join(self.snapshot, "metadata.json"))


def main():
    if len(sys.argv) > 1:
        assert sys.argv[1] == "forever"
        while True:
            updater = Updater()
            updater.update()
            sleep(10)
    else:
        updater = Updater()
        updater.update()


if __name__ == "__main__":
    main()
