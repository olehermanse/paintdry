import os
import sys
import copy
from time import sleep

import psycopg2

from secdb.utils import JsonFile, ensure_folder, ensure_json_file, shell, sha, timestamp
from secdb.database import Database
from secdb.modules.http import HTTPModule
from secdb.modules.lib import clear_get_cache, Discovery, Observation, Resource, ConfigTarget


class Updater:
    def __init__(self):
        self.database = Database()
        self.cache = {}

    def _process(self, identifier: str, module: str) -> tuple[list[Observation],list[Discovery]]:
        key = module + " - " + identifier
        if key in self.cache:
            return ([], [])
        self.cache[key] = True
        resource = Resource(identifier, [module])
        for module in resource.modules:
            match module:
                case "http":
                    return HTTPModule.process(resource)
                case other:
                    sys.exit(f"Target '{module}' not supported!")
        return ([], [])

    def process_discovery(self, discovery: Discovery):
        print("Discovery: " + discovery.resource)
        self.database.upsert_resource(Resource.from_discovery(discovery), discovery.source)

    def process_resource(self, entry: Resource):
        resource = entry.resource
        for module in entry.modules:
            results, discoveries = self._process(resource, module)
            for result in results:
                self.database.upsert_observations(result)
            for e in discoveries:
                self.process_discovery(e)

    def update_config(self, target: ConfigTarget):
        self.database.upsert_config(target)
        resource = Resource.from_target(target)
        self.database.upsert_resource(resource, "config.json")

    def update(self):
        clear_get_cache()

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
            target = ConfigTarget(target["resource"], target["module"])
            self.update_config(target)

        for resource in self.database.get_resources():
            self.process_resource(resource)

        # Commit snapshot
        metadata["last_update"] = {"time": time, "name": snapshot_name, "seq": seq}
        metadata.save()
        metadata.save(os.path.join(self.snapshot, "metadata.json"))

def forever():
    while True:
        updater = Updater()
        updater.update()
        sleep(10)

def once():
    updater = Updater()
    updater.update()
