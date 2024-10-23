import os
import sys
import copy
from time import sleep

import psycopg2

from utils import JsonFile, ensure_folder, ensure_json_file, shell, sha, timestamp
from database import Database
from modules.http import module_http


class Updater:
    def __init__(self):
        self.database = Database()
        self.cache = {}

    def _process(self, entry):
        identifier, module = entry["identifier"], entry["module"]
        key = module + " - " + identifier
        if key in self.cache:
            return ([], [])
        self.cache[key] = True
        match entry["module"]:
            case "http":
                return module_http(entry)
            case other:
                sys.exit(f"Target '{entry['type']}' in config not supported!")

    def process(self, entry):
        results, discoveries = self._process(entry)
        for e in results:
            self.database.upsert_observations(e)
        for e in discoveries:
            self.process(e)

    def update_config(self, entry):
        self.database.upsert_config(entry)

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
            self.update_config(target)
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
