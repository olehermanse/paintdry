import os
import sys
import json
import datetime
from time import sleep
from subprocess import Popen, PIPE, STDOUT


from secdb.utils import JsonFile, ensure_folder, timestamp
from secdb.database import Database
from secdb.modules.http import HTTPModule
from secdb.modules.lib import (
    clear_get_cache,
    Discovery,
    Observation,
    Resource,
    ConfigTarget,
)


def now() -> int:
    return int(datetime.datetime.now().timestamp())


class Updater:
    def __init__(self):
        self.database = Database()
        self.cache = {}
        self.externals = {}

    def handle_external_module(self, resource: Resource, module: str):
        config = JsonFile("config.json")
        if not module in self.externals:
            print(f"Starting '{module}' module")
            command = config["modules"][module]["command"]
            self.externals[module] = Popen(
                command,
                shell=True,
                text=True,
                encoding="utf-8",
                stdin=PIPE,
                stdout=PIPE,
                stderr=STDOUT,
            )

        print(f"Sending requests to '{module}' module for '{resource.resource}'")
        process: Popen = self.externals[module]
        request = {
            "operation": "discovery",
            "resource": resource.resource,
            "module": module,
            "timestamp": now(),
        }
        a = json.dumps(request)
        request["operation"] = "observation"
        b = json.dumps(request)
        process.stdin.write(a + "\n")
        process.stdin.write(b + "\n")
        process.stdin.flush()
        print(f"Sent requests to '{module}' module for '{resource.resource}'")

        discoveries = []
        while True:
            response = process.stdout.readline().strip()
            if not response:
                break
            o = json.loads(response)
            assert o["type"] == "discovery"
            del o["type"]
            o["modules"] = [o["module"]]
            del o["module"]  # TODO FIXME
            o["source"] = module
            result = Discovery(**o)
            discoveries.append(result)
        print(f"Received discoveries from '{module}' module for '{resource.resource}'")

        observations = []
        while True:
            response = process.stdout.readline().strip()
            if not response:
                break
            o = json.loads(response)
            assert o["type"] == "observation"
            del o["type"]
            result = Observation(**o)
            observations.append(result)

        print(f"Received discoveries from '{module}' module for '{resource.resource}'")

        return (observations, discoveries)

    def _process(
        self, identifier: str, module: str
    ) -> tuple[list[Observation], list[Discovery]]:
        key = module + " - " + identifier
        if key in self.cache:
            return ([], [])
        self.cache[key] = True
        resource = Resource(identifier, [module])
        for module in resource.modules:
            match module:
                case "http":
                    return HTTPModule.process(resource)
                case "dns":
                    return self.handle_external_module(resource, module)
                case other:
                    sys.exit(f"Target '{module}' not supported!")
        return ([], [])

    def process_discovery(self, discovery: Discovery):
        print("Discovery: " + discovery.resource)
        self.database.upsert_resource(
            Resource.from_discovery(discovery), discovery.source
        )

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
